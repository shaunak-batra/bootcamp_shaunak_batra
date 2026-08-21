# Cross-Asset Diversification Breakdown Monitor
**Stage:** Problem Framing & Scoping (Stage 01)

## Problem Statement

Multi-asset allocation rests on an empirical claim rather than a law: that equities,
government bonds, gold, broad commodities, and the dollar do not fall together. A
portfolio built across these five exposures is sized and risk-managed on the assumption
that their pairwise correlations sit near zero, or negative, most of the time. That
assumption does not always hold. In the second half of 2008, in March 2020, and through
much of 2022, correlations across this basket moved toward one at the same time realized
volatility spiked, and portfolios constructed to diversify equity risk instead moved as a
single leveraged position.

This project tracks whether that correlation structure is still intact, and is built to
say so the moment it starts to break, while a discretionary risk decision can still act
on it.

## Stakeholder & User

Decision owner: a portfolio manager or head of risk on a multi-asset desk, who can
reduce gross exposure or add a hedge. Operator: the risk analyst running the monitor and
producing the report the PM reads. Decision window: weekly refresh, with escalation the
moment the stress score crosses its threshold.

## Useful Answer & Decision

Descriptive and predictive: a current-state read on cross-asset correlation, combined
with a regime classification (normal or breaking down) and a near-term forecast of the
stress score's direction. Decision trigger: stress-score z-score crosses 2.0, or a flag
survives the multiple-testing correction used later in the project.

## Assumptions & Constraints

- The five ETF proxies (`SPY`, `TLT`, `GLD`, `DBC`, `UUP`) reasonably stand in for their
  asset classes, checked against published index-level correlation figures rather than
  assumed.
- Correlation regimes persist on the order of weeks rather than days.
- Free daily data only, via `yfinance`; backtest and monitoring only, no live execution;
  index-level ETFs, so capacity and liquidity are not constraints.

## Known Unknowns / Risks

The historical crisis windows used to evaluate this monitor are chosen with the benefit
of hindsight, which risks overstating the model's skill against labels selected after
the outcome was known. Each ETF proxy carries its own tracking behavior that can diverge
from the true asset class during exactly the stress this project is built to catch.
Only a small number of real crisis events exist in the available backtest history, a
thin sample for any supervised claim.

## Lifecycle Mapping

Goal → Stage → Deliverable

- Frame the problem and name a real decision it informs → Problem Framing & Scoping
  (Stage 01) → this scoping paragraph, persona, and repo skeleton
- Get real cross-asset data into the repo → Data Acquisition & Ingestion → raw pulls in
  `data/raw/`
- Turn raw prices into a clean, aligned return series → Data Preprocessing →
  `src/cleaning.py`
- Test the correlation-persistence assumption, define what counts as an outlier →
  Outlier Analysis → `src/outliers.py`
- Engineer the stress signal → Feature Engineering → `src/features.py`
- Classify and forecast the regime → Modeling → `src/model.py`
- Prove the signal is worth acting on → Evaluation & Risk Communication →
  `src/evaluation.py`

## Repo Plan

This assignment's own folder, `homework/homework01/`, holds only this README and a
stakeholder artifact in `docs/`; no data folders are needed at the framing stage. The
full project repository plan, with the complete methodology, lives in
[`project/README.md`](../../project/README.md).
