"""Calendar alignment and log returns.

Stage 06. The raw price frame arrives already inner-joined across tickers by
utils.fetch_prices, so the work here is the transformation from prices to a clean,
aligned return series that every later stage assumes.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def align_calendar(prices: pd.DataFrame) -> pd.DataFrame:
    """Sort, de-duplicate, and drop any row where a ticker is missing.

    An inner join across tickers is the point: a missing bar in one series must
    never be treated as a zero return in the others. Dropping the row costs one
    day of history and keeps every return honest.
    """
    out = prices.sort_index()
    out = out[~out.index.duplicated(keep="first")]
    return out.dropna(how="any")


def to_log_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Daily log returns.

    Log returns are used throughout because they add across time, which every
    rolling-window statistic downstream assumes. The first row is undefined and
    is dropped.
    """
    return np.log(prices / prices.shift(1)).dropna(how="any")


def fill_missing_median(df: pd.DataFrame, columns: list[str] | None = None) -> pd.DataFrame:
    """Fill gaps in the named numeric columns with that column's median.

    Not used on the main price path, which drops incomplete rows instead. Kept
    because the stage 06 deliverable asks for a fill helper, and because a median
    fill is the right tool if this pipeline is ever pointed at a series where
    dropping the row is too expensive.
    """
    out = df.copy()
    for col in (columns or out.select_dtypes("number").columns):
        out[col] = out[col].fillna(out[col].median())
    return out


def drop_missing(df: pd.DataFrame, threshold: float = 0.5) -> pd.DataFrame:
    """Drop any column missing more than `threshold` of its values."""
    frac = df.isna().mean()
    return df[frac[frac <= threshold].index].copy()


def normalize_data(df: pd.DataFrame, columns: list[str] | None = None) -> pd.DataFrame:
    """Min-max scale the named columns to [0, 1]."""
    out = df.copy()
    for col in (columns or out.select_dtypes("number").columns):
        lo, hi = out[col].min(), out[col].max()
        span = hi - lo
        out[col] = (out[col] - lo) / span if span else 0.0
    return out


def cleaning_report(prices: pd.DataFrame, returns: pd.DataFrame) -> dict:
    """What the cleaning step actually did, for the notebook to print."""
    return {
        "price_rows": len(prices),
        "return_rows": len(returns),
        "rows_lost_to_diff": len(prices) - len(returns),
        "price_start": str(prices.index.min().date()),
        "price_end": str(prices.index.max().date()),
        "na_in_returns": int(returns.isna().sum().sum()),
        "calendar_gaps_over_5d": int(
            (returns.index.to_series().diff().dt.days > 5).sum()
        ),
    }
