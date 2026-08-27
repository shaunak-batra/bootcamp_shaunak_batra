"""One pipeline task, runnable from the command line.

Stage 15. The point is that a scheduler should be able to invoke a single step
without importing the notebook or running everything before it. Each task reads
what it needs from disk and writes what it produces back to disk, so the steps
compose through the filesystem rather than through a single long-lived process.

    python -m src.run_step acquire
    python -m src.run_step features
    python -m src.run_step flags --pair SPY-TLT
    python -m src.run_step all --refit

Every task logs what it read, what it wrote, and how long it took, so a failure in
a scheduled run can be located without re-running anything.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import pandas as pd

from src import config
from src.pipeline import (CALIB_PATH, MODEL_PATH, latest_reading, run_pipeline,
                          step_acquire, step_features, step_flags, step_regime,
                          step_transform)
from src.utils import processed_dir, read_df

log = logging.getLogger("run_step")


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        stream=sys.stdout,
    )


def _require(path: Path, produced_by: str) -> pd.DataFrame:
    """Load an intermediate, failing with a message that says how to make it."""
    if not path.exists():
        raise SystemExit(
            f"missing {path}. Run `python -m src.run_step {produced_by}` first."
        )
    return read_df(path)


def task_acquire(args) -> dict:
    prices = step_acquire(save=True)
    return {"rows": len(prices), "start": str(prices.index.min().date()),
            "end": str(prices.index.max().date())}


def task_transform(args) -> dict:
    prices = _require(processed_dir() / "prices_wide.parquet", "acquire")
    returns = step_transform(prices, save=True)
    return {"rows": len(returns)}


def task_features(args) -> dict:
    returns = _require(processed_dir() / "returns_wide.parquet", "transform")
    features = step_features(returns, save=True)
    return {"rows": len(features), "columns": len(features.columns)}


def task_flags(args) -> dict:
    returns = _require(processed_dir() / "returns_wide.parquet", "transform")
    out = step_flags(returns, pair=args.pair)
    flags = out["flags"]
    path = processed_dir() / "flags.parquet"
    flags.to_frame("flag").to_parquet(path)
    log.info("wrote %s", path)
    return {"pair": args.pair, "flagged": int(flags.sum()), "days": len(flags)}


def task_regime(args) -> dict:
    returns = _require(processed_dir() / "returns_wide.parquet", "transform")
    out = step_flags(returns, pair=args.pair)
    regime = step_regime(out["series"], refit=args.refit)
    return {
        "refit": args.refit,
        "separation_sd": round(regime["fit"]["separation_pooled_sd"], 3),
        "state_means": [round(m, 4) for m in regime["fit"]["means"]],
        "model_path": str(MODEL_PATH),
    }


def task_all(args) -> dict:
    result = run_pipeline(refit=args.refit, save=True)
    return latest_reading(result)


TASKS = {
    "acquire": task_acquire,
    "transform": task_transform,
    "features": task_features,
    "flags": task_flags,
    "regime": task_regime,
    "all": task_all,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run one task of the diversification monitor pipeline.")
    parser.add_argument("task", choices=sorted(TASKS), help="which task to run")
    parser.add_argument("--pair", default="SPY-TLT",
                        help="asset pair for flags and regime (default SPY-TLT)")
    parser.add_argument("--refit", action="store_true",
                        help="refit the regime model instead of loading the saved one")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    _setup_logging(args.verbose)
    log.info("task=%s pair=%s refit=%s", args.task, args.pair, args.refit)

    started = time.perf_counter()
    try:
        summary = TASKS[args.task](args)
    except SystemExit:
        raise
    except Exception:
        log.exception("task %s failed", args.task)
        return 1

    elapsed = time.perf_counter() - started
    log.info("task %s finished in %.1fs", args.task, elapsed)
    print(json.dumps({"task": args.task, "elapsed_seconds": round(elapsed, 2),
                      **summary}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
