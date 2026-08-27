# Homework 11: Evaluation and Risk Communication

Bootstrap (600 resamples) vs gaussian confidence bands on a linear fit, a three-way scenario
comparison on missing-data handling (mean/median impute vs drop), and a subgroup residual
check by segment, on synthetic data with heavy-tailed (t, 3 df) noise and 5% missingness
built in on purpose.

Bootstrap CIs come out about 30% wider than gaussian ones (0.79 vs 0.61 average width), since
the gaussian assumption doesn't hold here. Mean and median imputation give nearly identical
MAE (1.278 vs 1.284); dropping the missing rows looks better (1.065) but isn't a fair
comparison since it's measured on fewer rows. Segment C's residuals are noticeably more spread
out than Segments A and B. The full stakeholder-facing writeup, with a bottom-line
recommendation, is in the notebook's summary section.

`src/evaluation.py` holds the imputation, fitting, and bootstrap helper functions, extracted
from the starter and reused throughout the notebook.
