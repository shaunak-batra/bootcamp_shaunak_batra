"""Data acquisition and storage helpers.

Stage 04 contributes the acquisition side (pulling prices from yfinance into
data/raw/), stage 05 the storage side (env-driven paths, format routing by file
suffix, reload validation). Both live here because they are the same concern:
getting data in and out of the repo reproducibly.
"""

from __future__ import annotations

import datetime as dt
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from src.config import PROCESSED_DIR, RAW_DIR, START_DATE, TICKERS

load_dotenv()


def _dir_from_env(var: str, default: str) -> Path:
    """Resolve a data directory from .env, falling back to the config default."""
    p = Path(os.getenv(var, default))
    p.mkdir(parents=True, exist_ok=True)
    return p


def raw_dir() -> Path:
    return _dir_from_env("DATA_DIR_RAW", RAW_DIR)


def processed_dir() -> Path:
    return _dir_from_env("DATA_DIR_PROCESSED", PROCESSED_DIR)


def timestamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S")


# --- acquisition ------------------------------------------------------------

def fetch_prices(tickers: list[str] | None = None, start: str = START_DATE,
                 end: str | None = None) -> pd.DataFrame:
    """Download daily adjusted closes for the basket, inner-joined across tickers.

    auto_adjust=True is not optional. Unadjusted closes silently break every return
    calculation across ex-dividend and split dates, which is the most common way a
    pipeline like this one ends up quietly wrong.

    The inner join means the usable history starts when the last ticker to list
    began trading, not when the first did.
    """
    import yfinance as yf

    tickers = tickers or TICKERS
    raw = yf.download(tickers, start=start, end=end, auto_adjust=True,
                      progress=False)
    close = raw["Close"][tickers]
    aligned = close.dropna(how="any")
    aligned.index.name = "date"
    return aligned


def validate_prices(df: pd.DataFrame, tickers: list[str] | None = None) -> dict:
    """Shape/coverage checks on a freshly pulled price frame."""
    tickers = tickers or TICKERS
    missing_cols = [t for t in tickers if t not in df.columns]
    return {
        "rows": len(df),
        "missing_columns": missing_cols,
        "na_total": int(df.isna().sum().sum()),
        "start": str(df.index.min().date()) if len(df) else None,
        "end": str(df.index.max().date()) if len(df) else None,
        "monotonic_index": bool(df.index.is_monotonic_increasing),
        "duplicate_dates": int(df.index.duplicated().sum()),
    }


# --- storage ----------------------------------------------------------------

def detect_format(path: str | Path) -> str:
    s = str(path).lower()
    if s.endswith(".csv"):
        return "csv"
    if s.endswith((".parquet", ".pq", ".parq")):
        return "parquet"
    raise ValueError(f"Unsupported format: {s}")


def write_df(df: pd.DataFrame, path: str | Path, index: bool = True) -> Path:
    """Write a frame, routing on file suffix and creating parent dirs as needed."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fmt = detect_format(p)
    if fmt == "csv":
        df.to_csv(p, index=index)
    else:
        try:
            df.to_parquet(p, index=index)
        except ImportError as e:
            raise RuntimeError(
                "Parquet engine not available. Install pyarrow or fastparquet."
            ) from e
    return p


def read_df(path: str | Path) -> pd.DataFrame:
    """Read a frame back, routing on suffix. Dates come back as a DatetimeIndex."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"No file at {p}")
    fmt = detect_format(p)
    if fmt == "csv":
        return pd.read_csv(p, index_col=0, parse_dates=True)
    try:
        return pd.read_parquet(p)
    except ImportError as e:
        raise RuntimeError(
            "Parquet engine not available. Install pyarrow or fastparquet."
        ) from e


def validate_roundtrip(original: pd.DataFrame, reloaded: pd.DataFrame) -> dict:
    """Confirm a saved frame came back the way it went in."""
    return {
        "shape_equal": original.shape == reloaded.shape,
        "columns_equal": list(original.columns) == list(reloaded.columns),
        "index_is_datetime": pd.api.types.is_datetime64_any_dtype(reloaded.index),
        "max_abs_diff": float((original - reloaded).abs().to_numpy().max())
        if original.shape == reloaded.shape else None,
    }
