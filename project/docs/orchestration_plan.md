# Orchestration plan

How this pipeline decomposes into schedulable tasks, what depends on what, and which
parts are worth automating now.

## Tasks

Each is runnable on its own through `python -m src.run_step <task>`.

| Task | Reads | Writes |
| --- | --- | --- |
| `acquire` | yfinance API | `data/raw/prices_<ts>.csv`, `data/processed/prices_wide.parquet` |
| `transform` | `data/processed/prices_wide.parquet` | `data/processed/returns_wide.parquet` |
| `features` | `data/processed/returns_wide.parquet` | `data/processed/features.parquet` |
| `flags` | `data/processed/returns_wide.parquet` | `data/processed/flags.parquet` |
| `regime` | `data/processed/returns_wide.parquet`, `model/regime_hmm.pkl` | `model/regime_hmm.pkl` when refitting |
| `report` | `features.parquet`, `flags.parquet`, `model/` | `reports/images/*.png`, `data/processed/annual_summary.csv` |
| `serve` | `model/`, all processed tables | long-running Flask process |

## Dependencies

```
acquire
   |
transform
   |     \
features  flags
   |        |  \
   |        |   regime
   \        |   /
       report
          |
        serve   (restart to pick up new state)
```

`features` and `flags` both depend only on `transform` and touch different outputs, so
they can run in parallel. `regime` depends on `flags` only because both derive the same
correlation series; if that series were persisted by `flags`, `regime` would depend on the
file instead and the two could also run in parallel. That refactor is not worth doing at
this size.

## Idempotency

| Task | Idempotent | Why |
| --- | --- | --- |
| `acquire` | No | Appends a new timestamped CSV each run. The Parquet copy is overwritten, so the derived state is idempotent; only the raw archive grows. |
| `transform` | Yes | Pure function of its input, overwrites its output. |
| `features` | Yes | Same. |
| `flags` | Yes | Same, given the same calibration constants. |
| `regime` | Yes when loading, No when refitting | Loading is deterministic. Refitting is seed-dependent and a fraction of starts collapse, which is why `--refit` is explicit rather than the default. |
| `report` | Yes | Overwrites figures and the summary table. |

The timestamped raw files are deliberate rather than an oversight. They are the only
record of what the upstream source actually returned on a given day, and that matters
because `yfinance` restates history occasionally. A retention job trimming files older
than a year is the right cleanup, not making the task overwrite.

## Logging and checkpoints

Every task logs its start, what it read, what it wrote, and its wall time to stdout, which
is what a scheduler captures. The checkpoints are the Parquet files themselves: because
each task reads from disk and writes to disk, a failure at any point leaves every earlier
output intact and the run resumes by invoking the failed task directly rather than
starting over.

`model/calibration.json` records the calibration constants and the timestamp of the run
that produced them. It is the single artifact to compare against when diagnosing whether
a change in output came from new data or from a changed model.

## Failure points and retries

**Network failure in `acquire`** is the common one and the only task worth retrying
automatically. Three attempts with exponential backoff, then fail the run. It is safe to
retry because a partial download writes nothing.

**Upstream schema change in `acquire`** should not be retried. `validate_prices` catches a
missing column or an empty frame, and retrying a structural change just fails three times
more slowly. Fail loudly and alert.

**A collapsed fit in `regime --refit`** must not be retried blindly either. `step_regime`
raises rather than saving a degenerate model, so the previous good model stays in place
and the correct response is a human looking at the separation statistic.

Everything downstream of `transform` is pure computation on local files. Those tasks
either work or have a bug, and a retry changes nothing.

## What to automate now, and what not to

Automate `acquire` through `report` as one daily scheduled job, because it is
deterministic, takes under a minute end to end, and produces the artifact a reader wants.
A single cron entry calling `python -m src.run_step all` covers it.

Do not automate `regime --refit`. The fit is seed-dependent, a collapse is possible, and
the walk-forward analysis showed the fitted state means drift across refits in a way that
would let the model gradually normalise the very regime change it exists to flag. Annual,
by hand, with someone looking at the separation number.

Do not automate redeployment of the API on new data. Restarting the process picks up new
state, and that is a deliberate action a person should take after looking at the daily
report.

This is deliberately built from the course's own tools rather than Airflow or Prefect. At
seven tasks with a linear dependency chain and a sub-minute runtime, a scheduler plus a
CLI entry point does the whole job, and a DAG framework would add a service to operate for
no benefit that could be pointed at.
