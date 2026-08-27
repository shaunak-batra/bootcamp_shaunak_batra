"""The stress signal: average correlation, Absorption Ratio, Turbulence Index.

Stage 09. Three ways of compressing a 5x5 covariance structure into one number,
built in increasing order of sophistication so the pipeline has a working
end-to-end signal before the more involved measures are added.

All three read the same input, a frame of daily log returns, and all three are
computed on a trailing window so that nothing at time t uses information from
after t.
"""

from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd

from src.config import AR_N_EIGENVECTORS, WINDOW


def pairwise_correlations(returns: pd.DataFrame, window: int = WINDOW) -> pd.DataFrame:
    """Rolling correlation for each of the n(n-1)/2 asset pairs.

    With five assets that is ten columns, one per pair, each holding the
    correlation of those two return series over the trailing `window` days,
    re-estimated every day.

    Sixty days is neither arbitrary nor sacred. It is short enough that the window
    clears a stale regime within about three months, and long enough that one
    unusual day cannot swing the estimate on its own. A 60-day correlation has a
    standard error around 1/sqrt(57), roughly 0.13, so moves smaller than about a
    quarter of a correlation point are inside the noise.
    """
    cols = list(returns.columns)
    roll = returns.rolling(window).corr()
    out = {}
    for a, b in combinations(cols, 2):
        out[f"{a}-{b}"] = roll.xs(a, level=1)[b]
    return pd.DataFrame(out).dropna(how="all")


def average_correlation(pair_corr: pd.DataFrame) -> pd.Series:
    """Mean of the ten pairwise correlations.

    The plainest stress measure: one number that rises when the basket as a whole
    starts moving as one thing instead of five.

    Worth being honest about its weakness, because it matters for this basket.
    Averaging signed correlations lets opposite moves cancel. If SPY-TLT rises
    from -0.5 to 0 (a hedge disappearing, which is bad) while some other pair
    falls from +0.5 to 0 (more diversification, which is good), the average does
    not move at all. For a basket built out of deliberately opposed assets, that
    cancellation is not a corner case, it is the normal situation. The absolute
    variant below exists for exactly that reason.
    """
    return pair_corr.mean(axis=1)


def average_abs_correlation(pair_corr: pd.DataFrame) -> pd.Series:
    """Mean of |correlation| across pairs.

    Answers a different question than the signed mean: how tightly is anything
    coupled to anything else, regardless of direction. A basket where every pair
    sits at -0.8 is strongly structured and this measure will say so, where the
    signed mean would report -0.8 and invite the reading that diversification is
    abundant.
    """
    return pair_corr.abs().mean(axis=1)


def absorption_ratio(returns: pd.DataFrame, window: int = WINDOW,
                     n_eigen: int = AR_N_EIGENVECTORS) -> pd.Series:
    """Share of basket variance explained by its leading principal components.

    Kritzman, Li, Page and Rigobon (2011). Take the covariance matrix of the
    trailing window, find its eigenvalues, and report

        AR = (sum of the largest n_eigen eigenvalues) / (sum of all eigenvalues)

    The intuition is about how many genuinely distinct things are driving the
    basket. Eigenvectors of a covariance matrix are uncorrelated portfolios, and
    each eigenvalue is that portfolio's variance. If the five assets move for five
    unrelated reasons, variance spreads across all five eigenvalues and the
    largest one accounts for a modest share. If one common factor starts driving
    everything, that factor loads into the first eigenvector and its eigenvalue
    swells while the rest collapse. AR rising means the effective number of bets
    in the basket is falling, even if no individual correlation looks alarming.

    Two implementation notes. The denominator is the sum of all eigenvalues, which
    is the trace of the covariance matrix, which is the sum of the individual asset
    variances. The paper writes it the second way and this writes it the first;
    they are the same number. And n_eigen is set to one because the paper fixes the
    count at "approximately 1/5th the number of assets", and one fifth of five is
    one.

    Uses eigvalsh rather than eig because a covariance matrix is symmetric, which
    guarantees real eigenvalues and lets the solver skip the general case.
    """
    R = returns.to_numpy()
    idx = returns.index
    out = {}
    for i in range(window, len(R) + 1):
        cov = np.cov(R[i - window:i].T)
        eigvals = np.linalg.eigvalsh(cov)[::-1]  # descending
        total = eigvals.sum()
        if total <= 0:
            continue
        out[idx[i - 1]] = eigvals[:n_eigen].sum() / total
    return pd.Series(out, name="absorption_ratio")


def turbulence_index(returns: pd.DataFrame, window: int = WINDOW,
                     min_history: int | None = None) -> pd.Series:
    """How statistically unusual today's joint return vector is.

    Kritzman and Li (2010), equation 2:

        d_t = (r_t - mu) @ inv(Sigma) @ (r_t - mu)'

    This is the squared Mahalanobis distance. The paper's own note is worth
    keeping straight: the Mahalanobis distance is the square root of the
    turbulence measure, so what is returned here is turbulence, not distance.

    The reason it beats "was today a big move" is the inverse covariance matrix.
    Plain Euclidean distance would treat a 2% move in a volatile asset the same as
    a 2% move in a calm one, and would have nothing to say about whether the
    combination made sense. Multiplying by inv(Sigma) rescales each direction by
    how much variance the basket historically has along it. Directions the assets
    usually move in together get divided by a large number and contribute little.
    Directions they historically never move in together get divided by a small
    number and contribute a lot.

    The practical effect: a day where stocks and gold both jump, which almost never
    happens, registers as turbulent even if neither move was individually large.
    A day where stocks fall hard and Treasuries rally, which is the normal
    flight-to-quality pattern, registers as fairly ordinary even though both moves
    were big.

    Under joint normality d_t has a chi-squared distribution with n degrees of
    freedom, so its expected value is n, which is 5 here. Readings well above 5
    are the interesting ones. Real returns are fatter-tailed than normal, so the
    realised mean runs higher than 5 and the chi-squared quantiles should be
    treated as a rough guide rather than an exact reference.

    mu and Sigma are estimated on all history strictly before day t, expanding as
    the sample grows. That avoids scoring a day against a covariance matrix that
    already contains it, which would drag the estimate toward the very observation
    being tested and understate how unusual it was.
    """
    R = returns.to_numpy()
    idx = returns.index
    start = min_history or window
    out = {}
    for i in range(start, len(R)):
        hist = R[:i]
        mu = hist.mean(axis=0)
        cov = np.cov(hist.T)
        try:
            inv = np.linalg.inv(cov)
        except np.linalg.LinAlgError:
            continue
        d = R[i] - mu
        out[idx[i]] = float(d @ inv @ d.T)
    return pd.Series(out, name="turbulence")


def diversification_ratio(returns: pd.DataFrame, window: int = WINDOW,
                          weights: np.ndarray | None = None) -> pd.Series:
    """How much variance reduction the basket is actually delivering.

    Choueifaty and Coignard (2008):

        DR = (w' sigma) / sqrt(w' Sigma w)

    The numerator is what the portfolio's volatility would be if every asset moved
    in lockstep, which is just the weighted average of the individual volatilities.
    The denominator is the volatility it actually has. The ratio is therefore the
    factor by which diversification is shrinking risk. DR = 1 means no benefit at
    all, every asset is moving together. Higher is better.

    This is included alongside the three stress measures because it answers the
    project's question more directly than any of them. Average correlation can stay
    flat while diversification collapses, if some pairs tighten and others loosen.
    DR cannot: it is a property of the whole covariance matrix and the actual
    weights, so it moves if and only if the portfolio's realised risk reduction
    moves. When the signed average correlation and DR disagree, DR is the one
    describing what a portfolio holder experiences.
    """
    R = returns.to_numpy()
    idx = returns.index
    n = R.shape[1]
    w = weights if weights is not None else np.repeat(1.0 / n, n)
    out = {}
    for i in range(window, len(R) + 1):
        cov = np.cov(R[i - window:i].T)
        sig = np.sqrt(np.diag(cov))
        denom = np.sqrt(w @ cov @ w)
        if denom <= 0:
            continue
        out[idx[i - 1]] = float((w @ sig) / denom)
    return pd.Series(out, name="diversification_ratio")


def build_feature_frame(returns: pd.DataFrame, window: int = WINDOW) -> pd.DataFrame:
    """Assemble every stress measure onto one aligned daily index."""
    pair_corr = pairwise_correlations(returns, window)
    frame = pd.DataFrame({
        "avg_corr": average_correlation(pair_corr),
        "avg_abs_corr": average_abs_correlation(pair_corr),
        "absorption_ratio": absorption_ratio(returns, window),
        "turbulence": turbulence_index(returns, window),
        "diversification_ratio": diversification_ratio(returns, window),
    })
    return frame.join(pair_corr, how="left").dropna(how="any")


def zscore(series: pd.Series, train_end: str | None = None) -> pd.Series:
    """Standardise a series using only the training period's mean and sd.

    Standardising on the full sample would leak: the mean and standard deviation
    would already contain the stress episodes the z-score is then used to detect,
    which flatters the detector. Restricting the moments to a training window keeps
    later readings genuinely out of sample.
    """
    ref = series.loc[:train_end] if train_end else series
    mu, sd = ref.mean(), ref.std()
    return (series - mu) / sd if sd else series * 0.0
