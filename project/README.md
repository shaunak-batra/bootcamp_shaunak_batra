# Cross-Asset Diversification Breakdown Monitor

## Running it

```bash
conda create -n fe-course python=3.11 -y
conda activate fe-course
pip install -r requirements.txt
python run.py
```

That runs everything: pulls the data, computes the stress measures, tests them, fits or
loads the regime model, executes the notebook, and regenerates every figure and the
exported report. It takes under a minute and prints where to read the results.

| Command | What it does |
| --- | --- |
| `python run.py` | Everything. The one to use. |
| `python run.py --quick` | Analysis only, skips the notebook. About three seconds. |
| `python run.py --check` | Verifies the environment and exits without changing anything. |
| `python run.py --serve` | Runs everything, then starts the API on port 5055. |
| `python run.py --refit` | Refits the regime model rather than loading the saved one. |

Start with `reports/final_report.md` for the findings, or
`reports/project_pipeline.html` to read every cell with its output and no Python
installed. `docs/project_summary.md` is the non-technical version.

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

## How the Monitor Works

Every asset in the five-ETF basket produces a daily closing price. The first
transformation turns five price series into five return series, because prices are
not comparable across assets of different scale, and a two-dollar move in `TLT`
means something different from a two-dollar move in `SPY`. Log returns solve this
and have the additional property that they sum across time, which every later
calculation in this pipeline depends on.

From returns, the monitor computes a rolling correlation matrix: for every pair of
the five assets, how closely their daily moves have tracked each other over the
last 60 trading days. There are ten such pairs. Sixty days is neither arbitrary nor
sacred; it is short enough that the window moves past a stale regime within a few
months, and long enough that a single unusual day does not swing the whole
estimate. That correlation matrix, re-estimated every day, is the raw material for
everything downstream.

Ten numbers a day is too much to watch by eye, so the monitor compresses them into
one stress score, in three increasingly refined versions built in sequence. The
plainest version is just the average of the ten correlations, a single number that
rises when the basket, on the whole, starts moving as one instead of five. The
second, the Absorption Ratio, asks a sharper question: if the five assets' daily
moves had to be explained by the smallest possible number of underlying factors,
how much of the actual movement would the single largest factor account for. In a
calm market no one factor dominates, each asset has its own reasons to move. In a
stress episode, one factor (broad risk aversion) starts explaining nearly
everything, and the Absorption Ratio rises to reflect that. The third, the
Turbulence Index, goes further still: rather than asking about correlation in the
abstract, it asks how statistically unusual today's specific combination of moves
is, given the historical relationship between all five assets. A day where stocks
and gold move together, which almost never happens, registers as turbulent even if
neither move alone was large.

Because a raw stress score is just a number with no built-in sense of what counts
as unusual, the monitor does not stop there. It runs a formal statistical test
asking whether the correlation regime has actually shifted, not merely wobbled,
using an Augmented Dickey-Fuller test on the rolling average-correlation series.
And because asking "is today unusual?" every single day for close to two decades is
itself a source of false alarms (run the same test enough times and something will
look significant purely by chance), the monitor does not flag a breakdown off a
single day's reading in isolation. It converts each day's correlation reading into
a proper test statistic via the Fisher z-transform, then runs the sequential
Cauchy combination test across the whole sequence of daily readings, which
controls how often the monitor is allowed to be wrong across its entire operating
history, not just on any one day. It also checks, separately, whether the apparent
spike survives the Forbes-Rigobon heteroskedasticity adjustment, since raw
correlation mechanically rises when volatility rises even with no real change in
how two assets relate to each other.

What comes out the other end is not a single number but a classification: a
two-state Hidden Markov Model, trained on the stress score's own history, decides
whether today more closely resembles the calm regime or the turbulent regime the
model has learned from the data, and estimates how likely the market is to still
be in that regime tomorrow. That classification, together with the underlying
stress score, its recent trend, and whichever specific asset pair is driving
today's reading, is what actually reaches the PM: not "something is different,"
but a specific, checkable claim, for example that correlation between gold and
equities has moved to its 95th percentile over the past three weeks, survives the
heteroskedasticity check, and the model estimates an 80 percent chance the
elevated regime persists into next week.

That is the whole pipeline, five transformations from raw price to a
decision-ready read: price to return, return to correlation, correlation to
stress score, stress score to regime, regime to report. The Methodology section
below is the exact math behind each of those five steps.

## Data

Five liquid ETFs stand in for their asset classes: `SPY` for US equities, `TLT` for long
Treasuries, `GLD` for gold, `DBC` for broad commodities, and `UUP` for the US dollar.
Daily bars are pulled via `yfinance`, with `auto_adjust=True`. Using unadjusted close
silently breaks return calculations across ex-dividend and split dates, and is the most
common source of a quietly wrong result in a pipeline like this one.

The five tickers do not all start trading on the same date. `SPY` (1993), `TLT` (2002),
and `GLD` (2004) have long histories; `DBC` began trading February 3, 2006, and `UUP`,
the youngest of the five, began February 20, 2007. Raw prices are aligned on an inner
join across all five tickers before any return is computed, so a missing bar in one
series is never treated as a zero return in the others, which also means the effective
start of the usable dataset is set by the last ticker to begin trading: late February
2007, not 2006. This still comfortably covers all three labeled crisis windows below.

## Methodology

**Returns.** Log returns are used throughout because they are additive across time,
which every rolling-window statistic below assumes:

$$r_{i,t} = \ln\left(\frac{P_{i,t}}{P_{i,t-1}}\right)$$

**Correlation structure.** A pairwise correlation matrix $C_t$ is computed over a
trailing window of $W = 60$ trading days, re-estimated daily. With $n = 5$ assets,
this gives $\binom{n}{2} = 10$ pairwise correlations at each point in time; $n$
denotes the asset count everywhere below except in the Fisher z-transform, which
uses the window $W$ instead, noted explicitly at that formula.

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

**Heteroskedasticity bias check.** Raw correlation is not volatility-neutral. Forbes
and Rigobon (2002) show that a correlation coefficient rises mechanically when
variance rises, even with no change in the true linear relationship between two
series, so part of any observed correlation spike during a crisis can be a
statistical artifact of higher volatility rather than genuine increased comovement.
Their adjustment,

$$\rho^{*} = \frac{\rho}{\sqrt{1 + \delta(1 - \rho^2)}}$$

where $\delta = \sigma_h^2 / \sigma_l^2 - 1$, $\rho$ is the correlation observed in
the high-volatility window, and $\sigma_h^2$, $\sigma_l^2$ are the return variance
in the high- and low-volatility windows, is computed alongside the raw stress score
as a robustness check. A flagged breakdown that survives this adjustment is a
materially stronger claim than one that only shows up in the unadjusted
correlation.

**Multiple-testing correction.** Flagging a breakdown on every trading day over a
backtest spanning close to two decades means running the same test thousands of
times on statistics that are not independent, because the rolling windows overlap
and consecutive test statistics end up correlated by construction. A fixed daily
threshold under repeated testing guarantees false alarms from repetition alone.
This is addressed by converting the rolling correlation to a proper test statistic
via the Fisher z-transform,

$$X_t = \left(\tanh^{-1}(\rho_t) - \tanh^{-1}(\rho_{\text{baseline}})\right)\sqrt{W-3}$$

using the same $W = 60$ trading-day window defined above, not the asset count $n$
used elsewhere in this section. It is approximately standard normal under "no
regime change," then applying the sequential Cauchy combination test of Bouamara,
Laurent, and Shi (2023) to the resulting sequence of daily p-values. The same
procedure, run separately on each of the ten pairwise correlations, attributes a
flagged day to a specific asset pair rather than only a global alarm.

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

- Get real cross-asset data into the repo → Data Acquisition & Ingestion (04) →
  `src/utils.py`, raw pulls in `data/raw/`
- Make that data reliably reloadable → Data Storage (05) → `src/utils.py`,
  `data/processed/`
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

```text
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

## Data Storage

Two folders, and the split between them is a rule about provenance rather than about
file format. `data/raw/` holds what came back from the source, unedited, with a
timestamp in the filename so a pull can be traced to when it happened. Nothing in the
pipeline writes back into `raw/`. `data/processed/` holds everything derived from it,
all of which is reproducible by re-running the notebook, and all of which can be
deleted without losing anything that cannot be rebuilt.

Raw pulls are CSV because the archival copy should be readable by anything, including a
text editor, twenty years from now. Derived tables are Parquet, which matters more than
it first appears: a CSV round trip silently converts a `DatetimeIndex` back into strings
unless every reader remembers to parse it, and a dtype that changes depending on who
loaded the file is the kind of defect that surfaces three stages downstream as an
inscrutable error. Parquet stores the schema alongside the data, so a frame comes back
the way it went in.

Paths come from the environment rather than being written into the code.
`DATA_DIR_RAW` and `DATA_DIR_PROCESSED` are read from `.env` by `src/utils.py`, falling
back to the values in `src/config.py` when unset, so the same code runs on a different
machine or a different disk layout without edits. `write_df` and `read_df` route on the
file suffix, create missing parent directories before writing, and raise a clear error
rather than a stack trace when a Parquet engine is absent.

`.env.example` is committed and documents which keys exist. `.env` is not committed and
holds the real values. The pipeline runs without any key at all, because the acquisition
path uses `yfinance`, which needs none; `ALPHAVANTAGE_API_KEY` is read only if the
acquisition step is switched to Alpha Vantage.

## Feature Definitions

Five features are computed from the returns frame, each on a trailing window so that
nothing at time $t$ uses information from after $t$.

`avg_corr` is the mean of the ten pairwise correlations. It is the plainest reading of
whether the basket is moving as one thing, and it carries a weakness worth stating
plainly: averaging signed correlations lets opposite moves cancel. A `SPY`-`TLT`
correlation rising from -0.5 to 0 is a hedge disappearing, and some other pair falling
from +0.5 to 0 is diversification improving, and the signed average reports neither.

`avg_abs_corr` is the mean of the absolute pairwise correlations. It answers how tightly
anything is coupled to anything else regardless of direction, which is the question the
signed average cannot answer for a basket built out of deliberately opposed assets.

`absorption_ratio` is the share of basket variance carried by the leading principal
component, defined in the Methodology section above. It rises when the effective number
of independent bets falls, which can happen without any single pairwise correlation
looking unusual.

`turbulence` is the squared Mahalanobis distance of the day's return vector from its
historical mean, also defined above. Its mean and covariance are estimated on all history
strictly before the day being scored, so a day is never measured against a covariance
matrix that already contains it.

`diversification_ratio` is the weighted average of the individual asset volatilities
divided by the actual portfolio volatility,

$$DR_t = \frac{w'\sigma}{\sqrt{w'\Sigma w}}$$

with equal weights. It is the factor by which diversification is shrinking risk, and a
value of 1.0 means none at all. Of the five it is the most direct answer to the question
this project asks, because it is a property of the whole covariance matrix rather than of
any one pair, and it moves if and only if the portfolio's realised risk reduction moves.

The ten individual pairwise correlations are carried alongside these so that a flagged
day can be attributed to a specific asset pair rather than reported as an unexplained
basket-level alarm.

## Setup and Usage

The environment is a conda env running Python 3.11 with pinned dependencies:

```bash
conda create -n fe-course python=3.11 -y
conda activate fe-course
pip install -r requirements.txt
```

The pins in `requirements.txt` are not decoration. `pandas` below 2.0 is compiled against
the NumPy 1.x C API, and NumPy 2.0 changed the size of the `dtype` struct, so an
old `pandas` against a new `numpy` fails at import with a binary incompatibility error
rather than anything that suggests what is actually wrong. The two have to move together.

To run the whole pipeline:

```bash
conda activate fe-course
cd project
jupyter lab notebooks/project_pipeline.ipynb     # then Run All
```

or headless, which is what a check should use:

```bash
jupyter nbconvert --to notebook --execute --inplace notebooks/project_pipeline.ipynb
```

The notebook pulls live data from `yfinance` on each run, so the final year's figures
move as new trading days arrive. Everything before the current year is fixed.

Individual modules are importable on their own, which is the point of keeping them out of
the notebook:

```python
from src.utils import fetch_prices
from src.cleaning import align_calendar, to_log_returns
from src.features import pairwise_correlations
from src.outliers import calibrate_baseline, correlation_pvalues, flag_breakdowns

returns = to_log_returns(align_calendar(fetch_prices()))
spytlt = pairwise_correlations(returns)['SPY-TLT'].dropna()
flags = flag_breakdowns(correlation_pvalues(spytlt, calibrate_baseline(spytlt)))
```

## Lifecycle Stage Map

Where each stage of the course lives in this repository.

| Stage | Deliverable | File |
| --- | --- | --- |
| 01 Framing | problem, stakeholder, methodology | `README.md` |
| 02 Tooling | pinned environment, config constants | `requirements.txt`, `src/config.py` |
| 04 Acquisition | yfinance pull, inner join, validation | `src/utils.py` |
| 05 Storage | env-driven paths, format routing | `src/utils.py` |
| 06 Preprocessing | calendar alignment, log returns | `src/cleaning.py` |
| 07 Outliers and risk | ADF, Fisher z, Cauchy combination, Forbes-Rigobon | `src/outliers.py` |
| 08 EDA | profiling, return diagnostics, gap report | `src/eda.py` |
| 09 Features | the five stress measures | `src/features.py` |
| 10 Modeling | two-state HMM, hysteresis baseline | `src/model.py` |
| 11 Evaluation | detection metrics, block bootstrap, exposure rule | `src/evaluation.py` |
| all | the narrative that runs everything | `notebooks/project_pipeline.ipynb` |
| all | calibration decisions and what the data disagreed with | `docs/methodology_notes.md` |

`docs/methodology_notes.md` is the companion to this file and is worth reading alongside
it. It records the places where the textbook version of a method had to be changed to
survive contact with this data, most importantly that the Fisher z-transform is
mis-scaled by roughly a factor of two on real returns, and it documents where the
premise stated at the top of this README does not match what the data shows.

## References

Bouamara, N., Laurent, S., & Shi, S. (2023). Sequential Cauchy Combination Test for
Multiple Testing Problems with Financial Applications. arXiv:2303.13406. Subsequently
published as A Stepwise Cauchy Combination Test for Multiple Testing Problems with
Financial Applications, *Journal of Financial Econometrics*, 23(5), 2025.

Forbes, K. J., & Rigobon, R. (2002). No Contagion, Only Interdependence: Measuring
Stock Market Comovements. *The Journal of Finance*, 57(5), 2223-2261.

Kritzman, M., & Li, Y. (2010). Skulls, Financial Turbulence, and Risk Management.
*Financial Analysts Journal*, 66(5), 30-41.

Kritzman, M., Li, Y., Page, S., & Rigobon, R. (2011). Principal Components as a Measure
of Systemic Risk. *The Journal of Portfolio Management*, 37(4), 112-126.
