# Homework 10b: Modeling, Time Series and Classification

Four leakage-safe features (`lag_1`, `roll_mean_5`, `roll_std_20`, `momentum_10`, all shifted
so nothing at time t sees information from t or later), a time-aware 80/20 split, and both
tracks from the assignment:

- Forecasting next-step return with `LinearRegression`: RMSE 0.01447 versus 0.01460 for a
  naive always-predict-zero baseline, barely better than not modeling at all.
- Classifying next-step direction with `LogisticRegression`: 57.3% accuracy against a 55.2%
  majority-class baseline, a real but small edge, with low recall (0.28) on up-days.

The synthetic data has a genuine regime shift at its midpoint (calmer/positive returns in the
first half, choppier/negative in the second), and the interpretation section in the notebook
ties both results back to that: the model trains mostly on the calm regime and is evaluated
more on the choppy one, which is exactly the kind of distribution shift this course's project
is built to detect and flag, not a synthetic-data quirk to ignore.
