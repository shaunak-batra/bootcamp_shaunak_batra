# Handoff plan

For whoever takes this over or is on call for it.

- **Run it by hand first.** `conda activate fe-course`, then `python -m src.pipeline`
  from `project/`. It prints the current reading as JSON and takes under a minute. If
  that works, everything else will.

- **Serving is one command.** `python app.py` starts the API on port 5055. The model and
  the current reading load once at startup, so the first request is fast and no request
  refits anything. Restarting the process is how you pick up new data.

- **The routes are `/health`, `/reading`, `/predict` (POST or GET with a path
  parameter), and `/history`.** `/reading` is the one a person wants: the current
  correlation, whether it is flagged, the regime, and the supporting measures.

- **Deployment target is a single small VM or container running the Flask app behind a
  scheduled daily pipeline run.** There is no database. State is four Parquet files in
  `data/processed/`, one pickle in `model/`, and one JSON in `model/calibration.json`.
  Losing all of it costs one pipeline run to rebuild, because everything derives from a
  public data source.

- **The daily job is `python -m src.pipeline`.** It is idempotent apart from appending a
  timestamped CSV in `data/raw/`. Running it twice in a day is harmless.

- **Alert thresholds and owners are in `docs/monitoring_plan.md`.** First response to any
  alert is a manual pipeline run compared against `model/calibration.json`.

- **Rollback is copying the previous `model/regime_hmm.pkl` back into place** and
  restarting the app. No migration, no schema, nothing else to undo.

- **Do not refit the regime model casually.** `step_regime(refit=True)` retrains and
  overwrites the saved model. The fit is seed-dependent, a fraction of starts collapse,
  and the pipeline raises rather than saving a collapsed one. Annual is the intended
  cadence, and the reason is in `docs/methodology_notes.md`.

- **Read `docs/methodology_notes.md` before changing any statistical parameter.** The
  variance inflation factor, the one-sided test, and the training-period baseline are
  each there because the textbook version demonstrably mis-fires on this data. Reverting
  any of them silently breaks the flags.

- **Know what this monitor does not do.** It detects the loss of diversifying
  relationships between holdings. It is not a crisis detector, and it was correctly
  silent through 2008 and March 2020. Anyone reading it as a drawdown alarm will
  misinterpret it.
