from __future__ import annotations

import pandas as pd


def detect_outliers_iqr(series: pd.Series, k: float = 1.5) -> pd.Series:
    """Boolean mask flagging values more than k * IQR beyond the 25th/75th percentile.

    Assumes the distribution is reasonably summarized by its quartiles; k controls
    strictness (higher k flags fewer points). NaNs are never flagged, since every
    comparison against a NaN is False. Raises ValueError on an empty series or k <= 0.
    """
    if series.empty:
        raise ValueError("series is empty, nothing to flag")
    if k <= 0:
        raise ValueError(f"k must be positive, got {k}")

    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    lower = q1 - k * iqr
    upper = q3 + k * iqr
    return (series < lower) | (series > upper)


def detect_outliers_zscore(series: pd.Series, threshold: float = 3.0) -> pd.Series:
    """Boolean mask flagging values with |z-score| > threshold.

    Uses the sample standard deviation (ddof=1), since a series like daily returns is
    treated as a sample drawn from a larger population, not the whole population itself.
    Assumes a roughly normal distribution; heavy tails will make this flag too many points.
    NaNs are never flagged. Raises ValueError on an empty series or threshold <= 0.
    """
    if series.empty:
        raise ValueError("series is empty, nothing to flag")
    if threshold <= 0:
        raise ValueError(f"threshold must be positive, got {threshold}")

    mu = series.mean()
    sigma = series.std(ddof=1)
    z = (series - mu) / (sigma if sigma else 1.0)
    return z.abs() > threshold


def winsorize_series(series: pd.Series, lower: float = 0.05, upper: float = 0.95) -> pd.Series:
    """Clip series to its [lower, upper] quantile range instead of dropping extreme points.

    Keeps every row (unlike the detect_* functions, which only flag), which matters for
    anything downstream that needs a fixed sample size. Raises ValueError if lower >= upper.
    """
    if not 0 <= lower < upper <= 1:
        raise ValueError(f"need 0 <= lower < upper <= 1, got lower={lower}, upper={upper}")

    lo = series.quantile(lower)
    hi = series.quantile(upper)
    return series.clip(lower=lo, upper=hi)
