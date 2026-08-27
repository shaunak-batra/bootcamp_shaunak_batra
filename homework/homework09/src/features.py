from __future__ import annotations

import pandas as pd


def add_spend_income_ratio(df: pd.DataFrame) -> pd.DataFrame:
    """Add spend_income_ratio: monthly_spend divided by income."""
    out = df.copy()
    out["spend_income_ratio"] = out["monthly_spend"] / out["income"]
    return out


def add_credit_score_band(df: pd.DataFrame) -> pd.DataFrame:
    """Add credit_score_band: standard FICO-style buckets for credit_score."""
    out = df.copy()
    bins = [-float("inf"), 579, 669, 739, 799, float("inf")]
    labels = ["Poor", "Fair", "Good", "Very Good", "Exceptional"]
    out["credit_score_band"] = pd.cut(out["credit_score"], bins=bins, labels=labels)
    return out


def add_region_onehot(df: pd.DataFrame) -> pd.DataFrame:
    """One-hot encode region into region_<name> columns."""
    return pd.get_dummies(df, columns=["region"], prefix="region")
