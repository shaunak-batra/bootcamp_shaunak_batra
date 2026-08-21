# Cross-Asset Diversification Breakdown Monitor

## Problem Statement

Multi-asset allocation rests on an empirical claim rather than a law: that equities,
government bonds, gold, broad commodities, and the dollar do not fall together. A
portfolio built across these five exposures is sized and risk-managed on the assumption
that their pairwise correlations sit near zero, or negative, most of the time. That
assumption does not always hold. In the second half of 2008, in March 2020, and through
much of 2022, correlations across this basket moved toward one at the same time realized
volatility spiked, and portfolios constructed to diversify equity risk instead moved as a
single leveraged position.

The consequence is asymmetric risk, not just higher risk. A desk that sizes exposure off
a correlation matrix estimated over a long, mostly calm sample will understate tail risk
precisely when the sample correlation stops describing the correlation actually in
effect. This project does not attempt to predict a drawdown. It tracks whether the
correlation structure a portfolio depends on is still intact, and is built to say so the
moment that structure starts to break, while a discretionary decision can still act on
it.

The multiple-testing correction used later in this project, under Multiple-testing
correction in the Methodology section, was not chosen by searching for one. It came
from the reverse direction: Bouamara, Laurent, and Shi's (2023) paper on the sequential
Cauchy combination test was read independently of this project, for its own sake, and
the fit turned out to be close enough to be worth building around rather than setting
aside. Their paper solves a specific problem: flagging a rare signal from a test
statistic repeated many times over, where the repetitions are not independent because
the underlying windows overlap. That is exactly the problem this monitor runs into
once it tries to flag a regime break every trading day for years on end: the same
repeated, serially dependent testing problem the authors built their method to solve,
just applied to daily cross-asset correlation instead of their own demonstrated case
of intraday drift-burst detection. That is a structural match, not
a topical one, which is why this project uses their specific procedure rather than a
more generic false-discovery correction.

## Stakeholder & User

Decision owner: a portfolio manager or head of risk on a multi-asset desk, who can
reduce gross exposure or add a hedge. Operator: the risk analyst running the monitor and
producing the report the PM reads. Decision window: weekly refresh, with escalation the
moment the stress score crosses its threshold.

## Useful Answer & Decision

Descriptive and predictive: a current-state read on cross-asset correlation, combined
with a regime classification (normal or breaking down) and a near-term forecast of the
stress score's direction. The deliverable is a regime label together with the evidence
behind it: the current stress score, its recent trajectory, and which specific asset
pair is driving the reading. It is not meant to be a bare signal with no evidence
attached. Decision trigger: stress-score z-score crosses 2.0, or a flag survives the
multiple-testing correction described below.

## Data

Five liquid ETFs stand in for their asset classes: `SPY` for US equities, `TLT` for long
Treasuries, `GLD` for gold, `DBC` for broad commodities, and `UUP` for the US dollar.
Daily bars are pulled via `yfinance` from 2006 onward, with `auto_adjust=True`. Using
unadjusted close silently breaks return calculations across ex-dividend and split dates,
and is the most common source of a quietly wrong result in a pipeline like this one. Raw
prices are aligned on an inner join across all five tickers before any return is
computed, so a missing bar in one series is never treated as a zero return in the
others.

## Methodology

**Returns.** Log returns are used throughout because they are additive across time,
which every rolling-window statistic below assumes:

$$r_{i,t} = \ln\left(\frac{P_{i,t}}{P_{i,t-1}}\right)$$

**Correlation structure.** A pairwise correlation matrix $C_t$ is computed over a
trailing window of $W = 60$ trading days, re-estimated daily. Five assets give
$\binom{5}{2} = 10$ pairwise correlations at each point in time.

**Stress score.** Three measures are computed, in increasing sophistication, built in
that order so the pipeline has a working end-to-end signal before the more involved ones
are added. The simplest is the average pairwise correlation:

$$S_t = \frac{2}{n(n-1)} \sum_{i \lt j} C_t[i,j]$$

The second is the Absorption Ratio of Kritzman, Li, Page, and Rigobon (2011): the share
of total variance in the basket explained by its leading principal component, from the
eigenvalues $\lambda_k$ of the rolling covariance matrix, sorted descending, with
$m = 1$ for a five-asset basket:

$$AR_t = \frac{\sum_{k=1}^{m}\lambda_k}{\sum_{k=1}^{n}\lambda_k}$$

A rising Absorption Ratio means the basket is increasingly explained by one common
factor rather than five independent ones. The third is the Turbulence Index of Kritzman
and Li (2010), a Mahalanobis distance measuring how unusual today's joint pattern of
returns is relative to its historical mean vector $\mu$ and covariance $\Sigma$:

$$d_t = (r_t - \mu)\Sigma^{-1}(r_t - \mu)'$$

**Regime testing.** An Augmented Dickey-Fuller test is run on the rolling average
correlation series to check the persistence assumption directly rather than
take it for granted: a rejection of the unit-root null over a sub-window is evidence the
correlation regime has shifted rather than merely drifted.

**Multiple-testing correction.** Flagging a breakdown on every trading day over an
eighteen-year backtest means running the same test thousands of times on statistics that
are not independent, because the rolling windows overlap and consecutive test statistics
end up correlated by construction. A fixed daily threshold under repeated testing
guarantees false alarms from repetition alone. This is addressed by converting the
rolling correlation to a proper test statistic via the Fisher z-transform,

$$X_t = \left(\tanh^{-1}(\rho_t) - \tanh^{-1}(\rho_{\text{baseline}})\right)\sqrt{n-3}$$

which is approximately standard normal under "no regime change," then applying the
sequential Cauchy combination test of Bouamara, Laurent, and Shi (2023) to the resulting
sequence of daily p-values. The same procedure, run separately on each of the ten
pairwise correlations, attributes a flagged day to a specific asset pair rather than
only a global alarm.

**Regime classification.** A two-state Gaussian Hidden Markov Model is fit on the stress
score series, states labeled normal and turbulent by their fitted means and decoded via
the Viterbi algorithm. A single-lag autoregression serves as a simple forecast of the
score's near-term direction, and a fixed z-score threshold is kept as the baseline the
more involved methods are measured against.

**Evaluation.** Output is graded against three labeled historical windows (2008, March
2020, and 2022) using precision, recall, and F1 at daily granularity, lead time between
the first elevated flag and each crisis's conventional start date, and the
false-positive rate outside those windows. A retrospective exposure-reduction exercise
translates the signal into a drawdown-avoided figure for the risk memo.

## Assumptions & Constraints

- The five ETF proxies reasonably stand in for their asset classes, checked against
  published index-level correlation figures rather than assumed.
- Correlation regimes persist on the order of weeks rather than days, checked via the
  ADF test above and the fitted HMM's state-persistence probabilities.
- The Fisher z-transformed rolling correlation is approximately normal under the
  no-change null, a standard approximation, checked empirically on this dataset before
  its p-values are relied on.
- Free daily data only, via `yfinance`; backtest and monitoring only, no live
  execution; index-level ETFs, so capacity and liquidity are not constraints.

## Known Unknowns / Risks

The three labeled crisis windows are chosen with the benefit of hindsight, risking
overstated model skill against labels selected after the outcome was known. Each ETF
proxy carries its own tracking behavior (`GLD` is a claim on gold, not gold itself) that
can diverge from the true asset class during exactly the stress this project is built to
catch. Only three real crisis events exist in the backtest history, a small and
imbalanced sample for any supervised claim, which is why the fitted regime model is
recalibrated periodically. The sequential Cauchy combination test is applied here to a
statistic the original authors did not test. Their published applications run at
different frequencies than the daily setting used here, so it is treated as an explicit
second layer on top of a working simple threshold, not a foundation taken on faith.

## Lifecycle Mapping

Goal → Stage → Deliverable

- Get real cross-asset data into the repo → Data Acquisition & Ingestion (04) → raw
  pulls in `data/raw/`
- Make that data reliably reloadable → Data Storage (05) → `data/processed/`
- Turn raw prices into a clean, aligned return series → Data Preprocessing (06) →
  `src/cleaning.py`
- Test the core assumption, define what counts as an outlier → Outlier Analysis (07) →
  `src/outliers.py`
- See the pattern before modeling it → Exploratory Data Analysis (08) → EDA notebook
- Engineer the stress signal → Feature Engineering (09) → `src/features.py`
- Classify and forecast the regime → Modeling (10) → `src/model.py`
- Prove the signal is worth acting on → Evaluation & Risk Communication (11) →
  `src/evaluation.py`
- Deliver it the way a PM reads it → Results Reporting (12) → `src/report.py`,
  `reports/`
- Make it reusable and self-running → Productization / Deployment / Orchestration
  (13-15) → `src/pipeline.py`

## Repo Plan

```
project/
├── data/
│   ├── raw/            direct pulls from yfinance, unedited
│   └── processed/      prices_wide.parquet, returns_wide.parquet
├── notebooks/
│   └── project_pipeline.ipynb   single narrative notebook, extended as work is added
├── src/
│   ├── config.py       tickers, window sizes, thresholds, crisis dates
│   ├── utils.py        shared helpers, including data acquisition and storage I/O
│   ├── cleaning.py      calendar alignment, log returns
│   ├── outliers.py      ADF test, threshold rule, SCC procedure
│   ├── features.py      average correlation, Absorption Ratio, Turbulence Index
│   ├── evaluation.py    precision/recall/F1, lead time, drawdown-avoided
│   ├── model.py         HMM, AR(1) forecast. Not in the instructor's example; added
│   │                    to cover modeling, which the example tree does not reach
│   ├── report.py        tear sheet. Added for the same reason
│   └── pipeline.py      orchestrates the above end to end
├── reports/
│   └── images/          saved figures
├── model/               fitted HMM and other saved model objects
├── docs/                persona memo, risk memo, system design notes
├── requirements.txt
├── .env.example
└── README.md
```

`config.py`, `utils.py`, `cleaning.py`, `outliers.py`, `features.py`, and
`evaluation.py` use the instructor's exact file names from the course's git-repository
structure document. `model.py`, `report.py`, and `pipeline.py` are added to cover parts
of the pipeline that example doesn't reach.

## References

Bouamara, N., Laurent, S., & Shi, S. (2023). Sequential Cauchy Combination Test for
Multiple Testing Problems with Financial Applications. arXiv:2303.13406.

Kritzman, M., & Li, Y. (2010). Skulls, Financial Turbulence, and Risk Management.
*Financial Analysts Journal*, 66(5), 30-41.

Kritzman, M., Li, Y., Page, S., & Rigobon, R. (2011). Principal Components as a Measure
of Systemic Risk. *The Journal of Portfolio Management*, 37(4), 112-126.
