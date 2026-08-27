from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import kurtosis, skew


def eda_summary(df: pd.DataFrame, numeric_cols=None) -> dict:
    """Return a dict with quick profiling stats and basic missingness.

    numeric_cols: optional list to limit numeric profiling.
    Also flags columns worth a second look before feature engineering: high
    missingness (>20%), near-zero variance, or one category dominating a
    non-numeric column (>90% of rows in a single value).
    """
    if numeric_cols is None:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    out = {}
    out["shape"] = df.shape
    out["dtypes"] = df.dtypes.to_dict()
    out["missing"] = df.isna().sum().to_dict()

    profile = df[numeric_cols].describe().T
    profile["skew"] = [skew(df[c].dropna()) for c in profile.index]
    profile["kurtosis"] = [kurtosis(df[c].dropna()) for c in profile.index]
    out["numeric_profile"] = profile

    flags = []
    missing_frac = df.isna().mean()
    for col, frac in missing_frac.items():
        if frac > 0.2:
            flags.append(f"{col}: {frac:.0%} missing")

    for col in numeric_cols:
        std = df[col].std()
        mean = df[col].mean()
        if std == 0 or (mean and abs(std / mean) < 0.01):
            flags.append(f"{col}: near-zero variance")

    for col in df.select_dtypes(exclude=[np.number]).columns:
        if df[col].dropna().empty:
            continue
        top_share = df[col].value_counts(normalize=True).iloc[0]
        if top_share > 0.9:
            flags.append(f"{col}: one category is {top_share:.0%} of rows")

    out["flags"] = flags
    return out
