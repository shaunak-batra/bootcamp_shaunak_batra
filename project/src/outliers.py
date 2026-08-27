"""Regime testing: ADF, the Fisher z test statistic, and the Cauchy combination correction.

Stage 07. This is where a correlation reading becomes a claim you can attach a
false-alarm rate to.

The chain is: rolling correlation -> Fisher z-transform into an approximately
normal test statistic -> p-value -> multiple-testing correction across the many
days the same test gets run on. Each link has a way of going quietly wrong, and
the constants that guard against that live in config.py.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from src.config import (FISHER_SD_INFLATION, SCC_ALPHA, SCC_FAMILY,
                        TEST_ALTERNATIVE, TRAIN_END, TRAIN_START, WINDOW)


# --- persistence -------------------------------------------------------------

def adf_test(series: pd.Series, **kwargs) -> dict:
    """Augmented Dickey-Fuller test on a correlation series.

    The project assumes correlation regimes persist on the order of weeks rather
    than days. That assumption is worth testing rather than asserting, and ADF is
    the standard way in.

    Read it the right way round. The null is a unit root, meaning the series
    wanders without being pulled back to any particular level. Failing to reject
    is consistent with a series that drifts between regimes and stays where it
    lands, which is what this project claims happens. Rejecting says the series
    is mean-reverting around a fixed level, which would undercut the idea that a
    correlation regime is a thing you can be in for months.

    One caution: ADF on a rolling correlation is testing a series built from
    overlapping windows, which is mechanically autocorrelated no matter what the
    underlying correlation does. A low p-value here should be read as evidence
    about the level, not proof of independence.
    """
    from statsmodels.tsa.stattools import adfuller

    clean = series.dropna()
    stat, pvalue, usedlag, nobs, crit, icbest = adfuller(clean, **kwargs)
    return {
        "adf_stat": float(stat),
        "p_value": float(pvalue),
        "used_lag": int(usedlag),
        "n_obs": int(nobs),
        "critical_values": {k: float(v) for k, v in crit.items()},
        "rejects_unit_root_5pct": bool(pvalue < 0.05),
    }


# --- test statistic ----------------------------------------------------------

def fisher_z(rho: pd.Series | np.ndarray) -> np.ndarray:
    """arctanh(rho), the Fisher z-transform.

    A sample correlation is bounded on [-1, 1] and its sampling distribution gets
    badly skewed as it approaches either end, because there is simply less room to
    move outward than inward. arctanh stretches the ends toward infinity and
    unskews the distribution, which is what makes a normal approximation usable.

    The useful property is that arctanh(r) has a variance of about 1/(W-3) that
    does not depend on the true correlation, so one standard error works
    everywhere on the scale instead of needing a different one near zero than
    near one.
    """
    r = np.asarray(rho, dtype=float)
    r = np.clip(r, -0.999999, 0.999999)  # arctanh is infinite at exactly +-1
    return np.arctanh(r)


def calibrate_baseline(pair_corr: pd.Series, train_start: str = TRAIN_START,
                       train_end: str = TRAIN_END,
                       use_measured_sd: bool = True) -> dict:
    """Estimate the null correlation level and the true z-scale from training data only.

    Two things get calibrated here, and both must come from a period the flags are
    not later evaluated on.

    The first is the baseline correlation, the level the test asks "has it moved
    away from this?". Taking it from the full sample would mean the threshold was
    partly set by the very episodes being detected.

    The second is the standard deviation of the z series, and this is the one that
    actually matters. Theory says arctanh(rho_t) should have standard deviation
    1/sqrt(W-3), about 0.132 for a 60-day window. That derivation assumes the
    returns inside the window are independent and normal. Real returns are neither.
    Fat tails and volatility clustering both inflate the variance of a correlation
    estimate, and measured on a stable stretch of this data the realised standard
    deviation came out near twice the theoretical value. Feeding the theoretical
    number into a normal CDF therefore produces p-values that are far too small: a
    nominal 5% test ends up rejecting something closer to 30% of the time.

    So the scale is measured, not assumed. `sd_used` below is what the p-values are
    actually computed with.

    By default the measured value is used directly. FISHER_SD_INFLATION in config
    is the fallback, and it is there for a reason worth knowing: the measurement
    only gets one independent observation per window length, so a nine-year
    training period yields around thirty-seven usable points. That is a genuinely
    noisy estimate of a standard deviation. Set use_measured_sd=False to fall back
    to the config constant if the measured number looks unstable on a different
    training period.
    """
    train = pair_corr.loc[train_start:train_end].dropna()
    z_train = fisher_z(train)

    theoretical_sd = 1.0 / np.sqrt(WINDOW - 3)
    # Stepping by the window length gives non-overlapping windows, so consecutive
    # points share no observations and the spread reflects real sampling noise
    # rather than the mechanical autocorrelation that overlap induces.
    z_indep = z_train[::WINDOW]
    realised_sd = float(np.std(z_indep, ddof=1))
    measured_inflation = realised_sd / theoretical_sd

    inflation = measured_inflation if use_measured_sd else FISHER_SD_INFLATION

    return {
        "baseline_rho": float(train.mean()),
        "baseline_z": float(np.mean(z_train)),
        "theoretical_sd": float(theoretical_sd),
        "realised_sd": realised_sd,
        "inflation_measured": float(measured_inflation),
        "inflation_config": FISHER_SD_INFLATION,
        "inflation_used": float(inflation),
        "sd_used": float(theoretical_sd * inflation),
        "n_train": int(len(train)),
        "n_independent": int(len(z_indep)),
    }


def correlation_pvalues(pair_corr: pd.Series, calib: dict,
                        alternative: str = TEST_ALTERNATIVE) -> pd.Series:
    """Turn each day's correlation into a p-value against the calibrated null.

    The statistic is the standardised distance of today's z from the baseline z:

        X_t = (arctanh(rho_t) - arctanh(rho_baseline)) / sd

    where sd is the measured scale from calibrate_baseline, not the textbook
    1/sqrt(W-3).

    The test is one-sided by default, and that choice carries real weight. The
    event this project cares about is correlation rising toward zero and above,
    the hedge failing. A correlation falling further below its baseline means the
    hedge is working better than usual, which is good news and must not raise an
    alarm. A two-sided test cannot tell those apart, and on this basket it flags
    the calm, strongly-hedged years hardest, which is precisely backwards.
    """
    z = fisher_z(pair_corr)
    x = (z - calib["baseline_z"]) / calib["sd_used"]

    if alternative == "greater":
        p = stats.norm.sf(x)
    elif alternative == "less":
        p = stats.norm.cdf(x)
    elif alternative == "two-sided":
        p = 2.0 * stats.norm.sf(np.abs(x))
    else:
        raise ValueError(f"unknown alternative: {alternative}")

    return pd.Series(np.clip(p, 1e-15, 1.0), index=pair_corr.index, name="p_value")


# --- Cauchy combination ------------------------------------------------------

def _tan_transform(p: np.ndarray) -> np.ndarray:
    """tan((0.5 - p) * pi), evaluated so it stays accurate in the tails.

    Calling tan directly on (0.5 - p) * pi loses precision exactly where it
    matters. For a very small p the argument sits next to pi/2, where tan is
    enormous and the floating-point representation of pi/2 is not exact, so the
    result is wrong without ever being infinite or raising anything. At p = 0 the
    naive form returns a large finite number that is really just the reciprocal of
    pi/2's rounding error.

    The identity tan(pi/2 - x) = cot(x) = 1/tan(x) fixes it. Writing
    tan((0.5 - p) * pi) as 1/tan(p * pi) moves the evaluation to a small argument,
    where tan(p * pi) is close to p * pi and computed accurately, so its reciprocal
    is accurate too. The mirrored identity handles p near 1.
    """
    p = np.asarray(p, dtype=float)
    p = np.clip(p, 1e-15, 1 - 1e-15)
    out = np.empty_like(p)

    lo = p < 0.25
    hi = p > 0.75
    mid = ~(lo | hi)

    out[lo] = 1.0 / np.tan(np.pi * p[lo])
    out[hi] = -1.0 / np.tan(np.pi * (1.0 - p[hi]))
    out[mid] = np.tan((0.5 - p[mid]) * np.pi)
    return out


def gcc_pvalue(pvalues: np.ndarray, weights: np.ndarray | None = None) -> float:
    """Global Cauchy combination p-value for a family of tests.

    Liu and Xie (2020). Transform each p-value onto the real line with
    tan((0.5 - p) * pi), take a weighted average, and read the result off a
    standard Cauchy distribution:

        T = sum_i w_i * tan((0.5 - p_i) * pi)
        p = 0.5 - arctan(T) / pi

    Why Cauchy and not something more obvious like Fisher's chi-squared
    combination: the Cauchy distribution has tails so heavy that the sum of
    Cauchy variables is Cauchy again with the same scale, and this survives
    almost any dependence structure between the individual tests. Fisher's method
    assumes independence and falls apart when the tests overlap. Here the tests
    are built from overlapping rolling windows and are heavily dependent by
    construction, so that robustness is the whole reason for the choice.

    The transform also does something useful on its own. tan((0.5 - p) * pi) blows
    up as p goes to zero, so one genuinely tiny p-value dominates the average and
    drags the combined statistic with it. A family of unremarkable p-values
    averages to near zero and the combination stays unremarkable.
    """
    p = np.asarray(pvalues, dtype=float)
    d = len(p)
    if d == 0:
        return 1.0
    w = weights if weights is not None else np.repeat(1.0 / d, d)
    t = float(np.sum(w * _tan_transform(p)))
    return float(0.5 - np.arctan(t) / np.pi)


def scc_reject(pvalues: np.ndarray, alpha: float = SCC_ALPHA) -> np.ndarray:
    """Sequential (stepwise) Cauchy combination test. Returns a boolean rejection mask.

    Bouamara, Laurent and Shi, published as "A Stepwise Cauchy Combination Test"
    in the Journal of Financial Econometrics (2025).

    The global test above answers "is anything going on in this family?" but not
    "which days?". The stepwise version recovers the individual answers. Sort the
    p-values ascending, then for the i-th smallest compute a Cauchy combination
    over the tail running from i to the end:

        T_(i) = sum_{j=i..d} w_j * tan((0.5 - p_(j)) * pi),  w_j = 1/(d-i+1)
        p~_(i) = 0.5 - arctan(T_(i)) / pi

    and reject H_(i) when p~_(i) <= alpha.

    The reason it works: testing the i-th hypothesis against the combination of
    everything from i upward means a small p-value is judged in the company of the
    larger ones, so it has to stand out from its own tail rather than clear a fixed
    bar. That borrows power across the family in the same way a step-down procedure
    does, while keeping the Cauchy combination's tolerance for dependent tests.

    Against Bonferroni this is materially less conservative under dependence, which
    is the paper's central claim and holds on this data. Against Benjamini-Hochberg
    it controls a stricter error rate: the probability of any false alarm at all,
    rather than the expected share of alarms that are false. For a monitor a person
    is supposed to act on, the stricter guarantee is the more useful one.
    """
    p = np.asarray(pvalues, dtype=float)
    d = len(p)
    if d == 0:
        return np.zeros(0, dtype=bool)

    order = np.argsort(p)
    p_sorted = p[order]
    trans = _tan_transform(p_sorted)

    # suffix means: T_(i) is the average of trans[i:], so build it from the back
    suffix_sum = np.cumsum(trans[::-1])[::-1]
    counts = np.arange(d, 0, -1)
    t_stats = suffix_sum / counts
    p_tilde = 0.5 - np.arctan(t_stats) / np.pi

    rej_sorted = p_tilde <= alpha
    rejected = np.zeros(d, dtype=bool)
    rejected[order] = rej_sorted
    return rejected


def _family_key(index: pd.DatetimeIndex, family: str) -> pd.Index:
    if family == "quarter":
        return index.to_period("Q")
    if family == "year":
        return index.to_period("Y")
    if family == "month":
        return index.to_period("M")
    if family == "all":
        return pd.Index(np.zeros(len(index), dtype=int))
    raise ValueError(f"unknown family: {family}")


def flag_breakdowns(pvalues: pd.Series, family: str = SCC_FAMILY,
                    alpha: float = SCC_ALPHA) -> pd.Series:
    """Apply the stepwise correction within each family and return daily flags.

    The family is the set of tests the error rate is controlled across, and the
    choice is a real one rather than a detail. The source paper corrects within a
    single trading day, over that day's minutes, and reports days with at least one
    rejection. The daily analogue used here is a calendar quarter.

    Correcting across the entire history in one family sounds stricter and more
    principled, but it is not a monitor: no flag can be issued until the last day
    of the sample is in hand. A quarter keeps the family small enough to retain
    power and short enough that the answer arrives while a risk decision can still
    act on it.
    """
    keys = _family_key(pvalues.index, family)
    out = pd.Series(False, index=pvalues.index, name="flag")
    for _, pos in pd.Series(range(len(pvalues)), index=keys).groupby(level=0):
        idx = pos.to_numpy()
        out.iloc[idx] = scc_reject(pvalues.to_numpy()[idx], alpha=alpha)
    return out


# --- volatility-artifact check -----------------------------------------------

def forbes_rigobon_adjust(rho_high: float, var_high: float, var_low: float) -> float:
    """Strip the volatility-driven part out of a correlation spike.

    Forbes and Rigobon (2002), equation 8:

        rho* = rho / sqrt(1 + delta * (1 - rho^2)),   delta = var_high/var_low - 1

    The problem it solves is mechanical rather than statistical. A correlation
    estimated over a high-volatility window is biased upward even when the true
    relationship between the two series has not changed at all. The reason is that
    correlation is covariance divided by the product of standard deviations, and
    when one market's variance jumps because of a shock that also passes through to
    the other, the numerator grows faster than the denominator.

    So the raw finding "correlations rose during the crisis" is exactly what you
    would see if nothing changed except that volatility went up. This adjustment
    asks what the correlation would have been at the calmer window's volatility.
    Note delta >= 0 whenever the high window really is more volatile, which makes
    the denominator at least one, so rho* is always pulled toward zero.

    A flagged breakdown that survives this is a substantially stronger claim than
    one that does not, because the obvious alternative explanation has been ruled
    out rather than ignored.
    """
    if var_low <= 0:
        raise ValueError("var_low must be positive")
    delta = var_high / var_low - 1.0
    return float(rho_high / np.sqrt(1.0 + delta * (1.0 - rho_high ** 2)))


def detect_outliers_iqr(series: pd.Series, k: float = 1.5) -> pd.Series:
    """Boolean mask flagging values more than k*IQR outside the quartiles."""
    if series.empty:
        raise ValueError("series is empty")
    q1, q3 = series.quantile(0.25), series.quantile(0.75)
    iqr = q3 - q1
    return (series < q1 - k * iqr) | (series > q3 + k * iqr)


def detect_outliers_zscore(series: pd.Series, threshold: float = 3.0) -> pd.Series:
    """Boolean mask flagging values more than `threshold` sample sds from the mean."""
    if series.empty:
        raise ValueError("series is empty")
    sd = series.std(ddof=1)
    if not sd:
        return pd.Series(False, index=series.index)
    return ((series - series.mean()) / sd).abs() > threshold
