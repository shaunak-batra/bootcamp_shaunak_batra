# Homework 09: Feature Engineering

Three features on a synthetic lending dataset, each in `src/features.py` and demonstrated in
the notebook with a rationale and a correlation check against `default_flag`:

- `spend_income_ratio`, a proportionality feature (spend relative to income, not spend alone).
- `credit_score_band`, a domain-informed bucketing of a continuous score into standard
  Poor/Fair/Good/Very Good/Exceptional bands.
- `region` one-hot encoded, the categorical feature. Chosen over label encoding (which would
  imply a false order between regions) and frequency encoding (which can collapse distinct
  categories that happen to share a similar row count).

`default_flag` in this synthetic dataset is generated independently of every other column, so
none of the correlation checks find a strong effect. That's expected here, the notebook explains
why, and the same checks would be read for real signal once run against the actual project data.
