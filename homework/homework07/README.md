# Homework 07: Outliers and Risk Assumptions

`src/outliers.py` has `detect_outliers_iqr`, `detect_outliers_zscore`, and `winsorize_series`,
each with input validation (positive k/threshold, a valid lower/upper range, no empty series)
added on top of the starter's sample implementations.

The notebook applies both detectors to a synthetic `daily_return` series with five shocks
injected in May 2022, then compares summary stats and a simple regression across three
treatments: all rows, IQR-filtered, and winsorized. The two detectors disagree in an
interesting way. Z-score at threshold=3 catches exactly the 5 real shocks, while IQR at k=1.5
also flags 4 ordinary trading days as outliers, since the shocks inflate the standard deviation
that Z-score relies on, but not the quartile fence IQR uses. The full writeup is in the
notebook's reflection section.
