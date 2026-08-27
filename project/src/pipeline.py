"""End-to-end run: prices in, regime call out.

Stage 13. The notebook is the narrative version of this. This is the one a
scheduler or an API calls, with no display, no plots, and a return value instead
of printed output.

Each step is a function that takes what the step before produced, so any of them
can be run alone against a saved intermediate. `run_pipeline` chains them.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import joblib
import pandas as pd

from src import config
from src.cleaning import align_calendar, to_log_returns
from src.evaluation import detection_metrics, label_series
from src.features import build_feature_frame, pairwise_correlations
from src.model import (calibrate_hysteresis, decode_states, fit_regime_hmm,
                       hysteresis_regime)
from src.outliers import (calibrate_baseline, correlation_pvalues,
                          flag_breakdowns)
from src.utils import fetch_prices, processed_dir, raw_dir, timestamp, write_df

log = logging.getLogger(__name__)

MODEL_DIR = Path("model")
MODEL_PATH = MODEL_DIR / "regime_hmm.pkl"
CALIB_PATH = MODEL_DIR / "calibration.json"
HEADLINE_PAIR = "SPY-TLT"


def step_acquire(save: bool = True) -> pd.DataFrame:
    """Pull prices and align them across tickers."""
    log.info("acquiring prices for %s", ",".join(config.TICKERS))
    prices = align_calendar(fetch_prices())
    if save:
        write_df(prices, raw_dir() / f"prices_{timestamp()}.csv")
        write_df(prices, processed_dir() / "prices_wide.parquet")
    log.info("prices: %d rows, %s to %s", len(prices),
             prices.index.min().date(), prices.index.max().date())
    return prices


def step_transform(prices: pd.DataFrame, save: bool = True) -> pd.DataFrame:
    """Prices to log returns."""
    returns = to_log_returns(prices)
    if save:
        write_df(returns, processed_dir() / "returns_wide.parquet")
    log.info("returns: %d rows", len(returns))
    return returns


def step_features(returns: pd.DataFrame, save: bool = True) -> pd.DataFrame:
    """Returns to the stress measures."""
    features = build_feature_frame(returns)
    if save:
        write_df(features, processed_dir() / "features.parquet")
    log.info("features: %d rows, %d columns", *features.shape)
    return features


def step_flags(returns: pd.DataFrame, pair: str = HEADLINE_PAIR) -> dict:
    """Calibrate on the training period, then test every day against that baseline."""
    series = pairwise_correlations(returns)[pair].dropna()
    calib = calibrate_baseline(series)
    pvalues = correlation_pvalues(series, calib)
    flags = flag_breakdowns(pvalues)
    log.info("flags: %d of %d days (%s families, alpha=%s)",
             int(flags.sum()), len(flags), config.SCC_FAMILY, config.SCC_ALPHA)
    return {"pair": pair, "series": series, "calibration": calib,
            "pvalues": pvalues, "flags": flags}


def step_regime(series: pd.Series, refit: bool = False,
                n_restarts: int = 20) -> dict:
    """Fit or load the regime model, then decode.

    Loads a saved model when one exists, because refitting on every call is both
    slow and non-deterministic in a way that matters: the fit is seed-dependent
    and a small fraction of starts collapse, so a served model should be the one
    that was checked, not whatever this run happens to produce.
    """
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    if MODEL_PATH.exists() and not refit:
        fit = joblib.load(MODEL_PATH)
        log.info("loaded regime model from %s", MODEL_PATH)
    else:
        log.info("fitting regime model, best of %d restarts", n_restarts)
        fit = fit_regime_hmm(series, n_states=2, n_restarts=n_restarts)
        if fit["degenerate"]:
            raise RuntimeError(
                "regime fit collapsed: both states share a mean. "
                "Refit with more restarts before serving this."
            )
        joblib.dump(fit, MODEL_PATH)
        log.info("saved regime model to %s (separation %.2f sd)",
                 MODEL_PATH, fit["separation_pooled_sd"])

    states = decode_states(fit, series)
    band = calibrate_hysteresis(fit)
    threshold_states = hysteresis_regime(series, band["enter"], band["exit"])
    return {"fit": fit, "states": states, "band": band,
            "threshold_states": threshold_states}


def run_pipeline(refit: bool = False, save: bool = True) -> dict:
    """Run every step in order and return the pieces a caller might want."""
    prices = step_acquire(save=save)
    returns = step_transform(prices, save=save)
    features = step_features(returns, save=save)
    flagged = step_flags(returns)
    regime = step_regime(flagged["series"], refit=refit)

    labels = label_series(flagged["flags"].index)
    metrics = detection_metrics(flagged["flags"], labels)

    if save:
        calib = dict(flagged["calibration"])
        calib["band"] = regime["band"]
        calib["generated"] = timestamp()
        CALIB_PATH.parent.mkdir(parents=True, exist_ok=True)
        CALIB_PATH.write_text(json.dumps(calib, indent=2), encoding="utf-8")

    return {
        "prices": prices,
        "returns": returns,
        "features": features,
        **flagged,
        "regime": regime,
        "metrics": metrics,
    }


def latest_reading(result: dict | None = None) -> dict:
    """The current state of the monitor, which is what a caller actually asks for.

    Returns the most recent correlation, whether it is flagged, which regime the
    model puts it in, and the supporting numbers a reader needs to judge it. The
    project's framing is explicit that a bare signal with no evidence attached is
    not the deliverable.
    """
    r = result or run_pipeline(save=False)
    series, flags = r["series"], r["flags"]
    states = r["regime"]["states"]
    feats = r["features"]
    day = series.index[-1]

    recent = series.tail(20)
    return {
        "as_of": str(day.date()),
        "pair": r["pair"],
        "correlation": round(float(series.iloc[-1]), 4),
        "correlation_20d_change": round(float(series.iloc[-1] - recent.iloc[0]), 4),
        "percentile_vs_history": round(float((series <= series.iloc[-1]).mean()), 4),
        "flagged": bool(flags.loc[day]) if day in flags.index else False,
        "regime": "elevated" if int(states.loc[day]) == 1 else "normal",
        "regime_persistence_days": round(
            float(r["regime"]["fit"]["expected_durations"][int(states.loc[day])]), 1),
        "diversification_ratio": round(float(feats["diversification_ratio"].iloc[-1]), 4),
        "absorption_ratio": round(float(feats["absorption_ratio"].iloc[-1]), 4),
        "turbulence": round(float(feats["turbulence"].iloc[-1]), 4),
        "baseline_correlation": round(float(r["calibration"]["baseline_rho"]), 4),
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    result = run_pipeline()
    reading = latest_reading(result)
    print(json.dumps(reading, indent=2))


if __name__ == "__main__":
    main()
