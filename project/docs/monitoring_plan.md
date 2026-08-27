# Monitoring plan

What can go wrong once this runs unattended, how it gets caught, and who acts.

## Failure modes

**Data layer: the upstream pull returns short or stale.** `yfinance` has no SLA and
changes shape without notice. Metric: row count returned by `step_acquire` against the
previous run, and the age of the newest bar. Threshold: fewer rows than last time, or a
newest bar more than four calendar days old. That four-day window covers a long weekend
without firing on every holiday.

**Data layer: a ticker silently drops out of the inner join.** If one series stops
updating, the join quietly truncates the whole dataset rather than erroring. Metric: the
per-ticker last-observation date. Threshold: any ticker more than two trading days behind
the others.

**Model layer: the regime fit collapses on refit.** A fraction of random starts converge
to a degenerate solution with both state means on the pooled mean, and every one of them
reports `converged = True`. Metric: `separation_pooled_sd` from `fit_regime_hmm`.
Threshold: below 1.5. `step_regime` already raises rather than saving a collapsed fit;
the monitor's job is to alert rather than fail silently into the previous model.

**Model layer: the calibration drifts out of date.** The Fisher variance inflation and
the baseline correlation are fitted on 2007 to 2015. If the return distribution changes,
the p-values stop meaning what they say. Metric: realised standard deviation of the
transformed correlation over a trailing two years, against the calibrated value.
Threshold: a ratio outside 0.7 to 1.4.

**Business layer: the flag rate goes to an extreme.** A monitor flagging every day or no
day for a quarter is not informative either way. Metric: flagged share per quarter.
Threshold: outside 2% to 60%.

## Alerting and ownership

Data and model alerts go to the risk analyst who operates the monitor. Business-layer
alerts go to the analyst and the portfolio manager together, because a flag rate at an
extreme changes how the output should be read rather than indicating a broken job.

First runbook step is the same for every alert: re-run `python -m src.pipeline` by hand
and compare its logged row counts, flag count and separation against the last good run
recorded in `model/calibration.json`. That single command distinguishes a transient
upstream failure from a real change in almost every case.

The analyst owns the daily job and the dashboards. The portfolio manager approves any
change to thresholds or to the exposure rule, since those change what the desk acts on.
Rollback is reverting `model/regime_hmm.pkl` to the previous saved copy, which the analyst
can do without approval because it restores a state that was already reviewed.

## Retraining

The regime model is refit annually, and only from a clean run where separation clears 1.5.
It is also refit on demand if the calibration-drift alert fires twice in a quarter.

Refitting is deliberately infrequent because the walk-forward test showed the fitted
"broken" state mean drifts steadily across refits, chasing the level rather than
describing a stable regime. Frequent refits would let the model normalise the very change
it exists to detect.
