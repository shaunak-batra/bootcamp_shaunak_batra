"""Profiling and exploratory views of the basket.

Stage 08. Nothing here changes the data. It exists so the notebook can ask what
the series look like before anything gets modelled on them.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import kurtosis, skew


def eda_summary(df: pd.DataFrame, numeric_cols: list[str] | None = None) -> dict:
    """Shape, dtypes, missingness, and a numeric profile with skew and kurtosis.

    Skew and kurtosis are here rather than in a footnote because they decide
    whether the rest of the pipeline's assumptions hold. The Fisher z-transform,
    the chi-squared reference for the Turbulence Index, and the Gaussian emissions
    in the HMM all assume something close to normality. Daily returns are reliably
    fat-tailed, and excess kurtosis is the number that says how badly.

    Flags mark columns worth attention before feature engineering: heavy
    missingness, near-zero variance, or a single category dominating.
    """
    if numeric_cols is None:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    profile = df[numeric_cols].describe().T
    profile["skew"] = [skew(df[c].dropna()) for c in profile.index]
    profile["excess_kurtosis"] = [kurtosis(df[c].dropna()) for c in profile.index]

    flags = []
    miss = df.isna().mean()
    for col, frac in miss.items():
        if frac > 0.2:
            flags.append(f"{col}: {frac:.0%} missing")
    for col in numeric_cols:
        sd, mu = df[col].std(), df[col].mean()
        if sd == 0 or (mu and abs(sd / mu) < 0.01):
            flags.append(f"{col}: near-zero variance")
    for col in df.select_dtypes(exclude=[np.number]).columns:
        if df[col].dropna().empty:
            continue
        top = df[col].value_counts(normalize=True).iloc[0]
        if top > 0.9:
            flags.append(f"{col}: one value covers {top:.0%} of rows")

    return {
        "shape": df.shape,
        "dtypes": df.dtypes.astype(str).to_dict(),
        "missing": df.isna().sum().to_dict(),
        "numeric_profile": profile,
        "flags": flags,
    }


def return_diagnostics(returns: pd.DataFrame) -> pd.DataFrame:
    """Per-asset return characteristics, annualised where that helps intuition.

    The normality column is the one to read. A Jarque-Bera test on daily returns
    essentially always rejects, so a rejection is not news. What the statistic's
    size tells you is how far from normal the series is, which sets how much to
    discount any p-value computed downstream under a normal assumption.
    """
    from scipy.stats import jarque_bera

    rows = {}
    for col in returns.columns:
        r = returns[col].dropna()
        jb, jb_p = jarque_bera(r)
        rows[col] = {
            "mean_daily": r.mean(),
            "vol_annual": r.std() * np.sqrt(252),
            "skew": skew(r),
            "excess_kurtosis": kurtosis(r),
            "jarque_bera": jb,
            "jb_p_value": jb_p,
            "min": r.min(),
            "max": r.max(),
        }
    return pd.DataFrame(rows).T


def rolling_gap_report(index: pd.DatetimeIndex, max_gap_days: int = 5) -> dict:
    """Look for holes in the trading calendar.

    A rolling window that spans a missing stretch is not the window it claims to
    be. Weekends and holidays produce gaps of two to four days as a matter of
    course, so only gaps beyond that are worth reporting.
    """
    diffs = index.to_series().diff().dt.days.dropna()
    big = diffs[diffs > max_gap_days]
    return {
        "n_observations": len(index),
        "start": str(index.min().date()),
        "end": str(index.max().date()),
        "max_gap_days": int(diffs.max()) if len(diffs) else 0,
        "n_gaps_over_threshold": int(len(big)),
        "largest_gaps": {str(d.date()): int(v) for d, v in big.nlargest(5).items()},
    }


def correlation_snapshot(returns: pd.DataFrame, window: tuple[str, str] | None = None
                         ) -> pd.DataFrame:
    """Full correlation matrix over a period, for eyeballing the basket's structure."""
    r = returns.loc[window[0]:window[1]] if window else returns
    return r.corr()
