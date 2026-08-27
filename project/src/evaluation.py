"""Is the signal worth acting on?

Stage 11. Detection metrics against labelled windows, bootstrap intervals around
those metrics, scenario sensitivity, and the volatility-artifact check that has to
pass before a flagged correlation move can be called real.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import CRISIS_WINDOWS, WINDOW
from src.outliers import forbes_rigobon_adjust


# --- detection metrics -------------------------------------------------------

def label_series(index: pd.DatetimeIndex,
                 windows: dict[str, tuple[str, str]] | None = None) -> pd.Series:
    """Mark each day 1 if it falls inside a labelled crisis window, else 0."""
    windows = windows or CRISIS_WINDOWS
    y = pd.Series(0, index=index, name="label")
    for _, (start, end) in windows.items():
        y.loc[start:end] = 1
    return y


def _confusion(f: np.ndarray, y: np.ndarray) -> dict:
    """Confusion counts and the metrics derived from them, on plain arrays.

    Kept separate from detection_metrics because the bootstrap resamples blocks
    with replacement, which produces repeated dates. Any index-aligned join on
    that fails, so the resampled path works positionally instead.
    """
    f = f.astype(int)
    y = y.astype(int)
    tp = int(((f == 1) & (y == 1)).sum())
    fp = int(((f == 1) & (y == 0)).sum())
    fn = int(((f == 0) & (y == 1)).sum())
    tn = int(((f == 0) & (y == 0)).sum())

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    return {
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": precision, "recall": recall, "f1": f1,
        "base_rate": float(y.mean()) if len(y) else 0.0,
        "flag_rate": float(f.mean()) if len(f) else 0.0,
        "false_positive_rate": fp / (fp + tn) if (fp + tn) else 0.0,
        "n": int(len(f)),
    }


def detection_metrics(flags: pd.Series, labels: pd.Series) -> dict:
    """Precision, recall, F1 and the confusion counts at daily granularity.

    Which one matters depends on the cost being managed, and for this monitor they
    are not symmetric. A false positive tells a desk to cut exposure during a calm
    period, which costs return. A false negative leaves the book exposed through a
    breakdown, which costs a great deal more. That argues for weighting recall
    above precision.

    The base rate is worth printing alongside these, because with labelled windows
    covering a small share of the sample a detector that fires constantly can post
    a respectable-looking recall while being useless.
    """
    j = pd.concat([flags.astype(int).rename("f"), labels.rename("y")],
                  axis=1, join="inner").dropna()
    return _confusion(j.f.to_numpy(), j.y.to_numpy())


def lead_time(flags: pd.Series, windows: dict | None = None,
              lookback_days: int = 250) -> dict:
    """Days between the first sustained flag and each labelled window's start.

    Positive means the monitor fired before the window opened, which is the only
    case where it could have informed a decision. Negative means it confirmed
    something already underway, which is still informative but is not early
    warning and should not be reported as if it were.

    Only flags inside `lookback_days` before the start count, so an unrelated flag
    years earlier is not credited as a prediction.
    """
    windows = windows or CRISIS_WINDOWS
    out = {}
    for name, (start, _) in windows.items():
        start_ts = pd.Timestamp(start)
        prior = flags.loc[start_ts - pd.Timedelta(days=lookback_days):start_ts]
        fired = prior[prior.astype(bool)]
        out[name] = int((start_ts - fired.index[0]).days) if len(fired) else None
    return out


# --- uncertainty -------------------------------------------------------------

def bootstrap_metric(flags: pd.Series, labels: pd.Series, metric: str = "f1",
                     n_boot: int = 1000, block: int = WINDOW,
                     seed: int = 42, alpha: float = 0.05) -> dict:
    """Block bootstrap confidence interval for a detection metric.

    An ordinary bootstrap resamples individual days, which assumes they are
    independent. They are not: both the flags and the labels come in runs lasting
    weeks or months, and resampling day by day shatters that structure and
    produces an interval far too narrow to believe.

    The moving block bootstrap resamples contiguous blocks instead, so the
    within-block dependence survives into each replicate. Block length is set to
    the correlation window, since that is the horizon over which these series are
    mechanically autocorrelated by construction.
    """
    rng = np.random.default_rng(seed)
    j = pd.concat([flags.astype(int).rename("f"), labels.rename("y")],
                  axis=1, join="inner").dropna()
    n = len(j)
    if n < block * 2:
        raise ValueError("series too short for this block length")

    f_all = j.f.to_numpy()
    y_all = j.y.to_numpy()
    n_blocks = int(np.ceil(n / block))
    starts_pool = np.arange(0, n - block + 1)
    stats = []
    for _ in range(n_boot):
        starts = rng.choice(starts_pool, size=n_blocks, replace=True)
        idx = np.concatenate([np.arange(s, s + block) for s in starts])[:n]
        stats.append(_confusion(f_all[idx], y_all[idx])[metric])

    lo, hi = np.percentile(stats, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return {"metric": metric, "point": _confusion(f_all, y_all)[metric],
            "mean": float(np.mean(stats)), "lo": float(lo), "hi": float(hi),
            "n_boot": n_boot, "block": block}


# --- robustness --------------------------------------------------------------

def volatility_artifact_check(returns: pd.DataFrame, pair: tuple[str, str],
                              high_window: tuple[str, str],
                              low_window: tuple[str, str]) -> dict:
    """Does a correlation move survive the Forbes-Rigobon adjustment?

    The competing explanation for any correlation spike during stress is that
    nothing about the relationship changed and only volatility rose, which inflates
    a correlation estimate on its own. This computes the raw correlation in the
    high-volatility window, then asks what it would have been at the calm window's
    volatility.

    If the adjusted number stays close to the raw one, the move is about the
    relationship. If it collapses back toward the calm-period level, the move was
    mostly an artifact and should not be reported as a regime change.
    """
    a, b = pair
    hi = returns.loc[high_window[0]:high_window[1], [a, b]].dropna()
    lo = returns.loc[low_window[0]:low_window[1], [a, b]].dropna()
    if len(hi) < 10 or len(lo) < 10:
        raise ValueError("not enough observations in one of the windows")

    rho_high = float(hi[a].corr(hi[b]))
    rho_low = float(lo[a].corr(lo[b]))
    var_high = float(hi[a].var())
    var_low = float(lo[a].var())

    adjusted = forbes_rigobon_adjust(rho_high, var_high, var_low)
    return {
        "rho_high_raw": rho_high,
        "rho_low": rho_low,
        "rho_high_adjusted": adjusted,
        "delta_raw": rho_high - rho_low,
        "delta_adjusted": adjusted - rho_low,
        "variance_ratio": var_high / var_low,
        "artifact_share": (
            1.0 - (adjusted - rho_low) / (rho_high - rho_low)
            if abs(rho_high - rho_low) > 1e-9 else float("nan")
        ),
    }


def scenario_table(series: pd.Series, flag_fn, scenarios: dict) -> pd.DataFrame:
    """Re-run the flagging logic under alternative assumptions and tabulate the shift.

    Every result in this project rests on choices that could reasonably have gone
    another way: the window length, the significance level, where the baseline is
    calibrated. A single set of flags reported without that context invites the
    reader to treat one path through those choices as the answer.
    """
    rows = []
    for name, kwargs in scenarios.items():
        flags = flag_fn(series, **kwargs)
        rows.append({
            "scenario": name,
            **{k: str(v) for k, v in kwargs.items()},
            "flagged_days": int(flags.sum()),
            "flag_rate": float(flags.mean()),
            "first_flag": str(flags[flags].index.min().date()) if flags.any() else None,
        })
    return pd.DataFrame(rows)


def drawdown_avoided(returns: pd.Series, flags: pd.Series,
                     reduce_to: float = 0.5, lag: int = 1) -> dict:
    """What the signal would have been worth as an exposure rule.

    Translates flags into the only currency the decision-maker actually cares
    about. On a flagged day the position is cut to `reduce_to` of full size, and
    the comparison is against holding full size throughout.

    The lag matters and is not a formality. A flag computed from today's close
    cannot be acted on until tomorrow, so the position change is applied one day
    late. Without that lag the backtest quietly assumes trades happen at prices
    that were not knowable, which is the most common way a result like this ends
    up overstated.
    """
    j = pd.concat([returns.rename("r"), flags.astype(int).rename("f")],
                  axis=1, join="inner").dropna()
    exposure = 1.0 - (1.0 - reduce_to) * j.f.shift(lag).fillna(0)
    strat = j.r * exposure

    def max_dd(x):
        curve = x.cumsum()
        return float((curve - curve.cummax()).min())

    return {
        "buy_hold_total": float(j.r.sum()),
        "managed_total": float(strat.sum()),
        "buy_hold_max_drawdown": max_dd(j.r),
        "managed_max_drawdown": max_dd(strat),
        "drawdown_avoided": max_dd(strat) - max_dd(j.r),
        "days_reduced": int(j.f.sum()),
        "reduce_to": reduce_to,
        "lag_days": lag,
    }
