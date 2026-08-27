from __future__ import annotations

import pandas as pd


def fill_missing_median(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Return a copy of df with NaNs in the given numeric columns filled by that column's median."""
    out = df.copy()
    for col in columns:
        out[col] = out[col].fillna(out[col].median())
    return out


def drop_missing(df: pd.DataFrame, threshold: float = 0.5) -> pd.DataFrame:
    """Return a copy of df with any column dropped whose fraction of missing values exceeds threshold.

    A column that's mostly empty (say, 70% NaN) doesn't have enough signal left to impute
    reliably, so it gets dropped instead of filled.
    """
    missing_frac = df.isna().mean()
    keep_cols = missing_frac[missing_frac <= threshold].index
    return df[keep_cols].copy()


def normalize_data(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Return a copy of df with the given numeric columns min-max scaled to the 0-1 range."""
    out = df.copy()
    for col in columns:
        col_min, col_max = out[col].min(), out[col].max()
        span = col_max - col_min
        out[col] = (out[col] - col_min) / span if span else 0.0
    return out
