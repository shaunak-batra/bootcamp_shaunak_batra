# Lifecycle framework guide

One row per stage: what it produced, where it lives, and the decision that stage forced.

| Stage | Deliverable | File | The decision made |
| --- | --- | --- | --- |
| 01 Problem framing | Problem, stakeholder, useful answer, risks | `README.md` | Frame it as monitoring whether a correlation structure is intact, not as predicting drawdowns. Those turned out to be different questions. |
| 02 Tooling setup | Pinned environment, config constants | `requirements.txt`, `src/config.py` | Pin `numpy` and `pandas` together. An old pandas against NumPy 2.x fails at import with a binary incompatibility that says nothing useful. |
| 04 Data acquisition | yfinance pull, inner join, validation | `src/utils.py` | `auto_adjust=True` and an inner join across tickers. Unadjusted closes turn dividends into fake returns; a forward fill turns a non-trading day into a fake zero return. |
| 05 Data storage | Env-driven paths, format routing | `src/utils.py` | CSV for the raw archive, Parquet for derived tables. A CSV round trip loses the datetime dtype unless every reader remembers to parse it. |
| 06 Preprocessing | Calendar alignment, log returns | `src/cleaning.py` | Log returns, because every rolling statistic downstream treats a window as a sum, and that is only exactly right for logs. |
| 07 Outliers and risk | ADF, Fisher z, Cauchy combination, Forbes-Rigobon | `src/outliers.py` | Measure the Fisher variance rather than assume it. The textbook `1/sqrt(W-3)` is off by roughly a factor of two on real returns, which turns a nominal 5% test into a 30% one. |
| 08 EDA | Profiling, return diagnostics, gap report | `src/eda.py` | Report excess kurtosis prominently, because it is what justifies the variance correction in stage 07 rather than being a decorative statistic. |
| 09 Feature engineering | Five stress measures | `src/features.py` | Keep the measures separate instead of blending them. They are close to mutually uncorrelated on this data, so an average would destroy what each one knows. |
| 10 Modeling | Two-state HMM, hysteresis baseline | `src/model.py` | Take the best of twenty restarts and check separation explicitly. A fraction of fits collapse to one Gaussian and every one of them reports `converged = True`. |
| 11 Evaluation | Detection metrics, block bootstrap, exposure rule | `src/evaluation.py` | Block bootstrap rather than ordinary. Flags and labels both come in runs, and resampling day by day would produce an interval far too narrow to believe. |
| 12 Reporting | Stakeholder memo | `reports/final_report.md`, `reports/README.md` | A written report, because the headline number needs its caveat in the same place or a reader draws the wrong conclusion from it. |
| 13 Productization | Pipeline module, Flask API, saved model | `src/pipeline.py`, `app.py`, `model/regime_hmm.pkl` | Load the model and the reading once at startup. Refitting per request would be slow and, because the fit is seed-dependent, would give different answers to identical calls. |
| 14 Deployment and monitoring | Failure modes, thresholds, ownership | `docs/monitoring_plan.md`, `docs/handoff_plan.md` | Refit annually rather than continuously, because frequent refits let the model normalise the regime change it exists to detect. |
| 15 Orchestration | Task decomposition, CLI runner | `docs/orchestration_plan.md`, `src/run_step.py` | Compose tasks through the filesystem. Each writes its output, so a failure leaves earlier work intact and the run resumes at the failed step. |
| 16 Lifecycle review | This guide, the plain-language summary | `docs/lifecycle_framework_guide.md`, `docs/project_summary.md` | Document where the data contradicted the original premise rather than quietly adjusting the premise to match. |

## The single most consequential decision

Stage 07's variance correction. Without it roughly a quarter of all days flag before any
multiple-testing correction is applied, which is not a signal, and every downstream stage
would have been built on noise. It was only found by measuring the realised spread of the
transformed correlation on a stable stretch of data and comparing it to what theory
predicted, which is a check that is easy to skip.

## Where the project and the data disagree

The framing in `README.md` states that correlations across this basket moved toward one in
2008, March 2020, and 2022. Measured directly, that holds for 2022 only. In 2008 and 2020
the stock-bond correlation went to about -0.53 against a full-sample -0.28, meaning the
hedge worked roughly twice as well as usual during both. The basket holds flight-to-quality
assets deliberately, and in a flight to quality those rally while equities fall.

This is recorded rather than resolved. The premise was kept as written and the monitor was
built to it; what changed is that the evaluation now reports honestly that two of its three
labelled events are not instances of the phenomenon being detected. `docs/methodology_notes.md`
has the measurements.
