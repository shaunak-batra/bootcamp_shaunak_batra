# Homework 10a: Modeling, Linear Regression

`LinearRegression` fit on a synthetic four-factor dataset (market excess return, size, value,
momentum) against an asset's excess return, on an 80/20 time-ordered split. Baseline R2 is
0.368, RMSE 0.00847.

Residual diagnostics check all four assumptions with an actual statistic behind each one, not
just a plot read by eye: a Shapiro-Wilk test for normality (doesn't reject, p is about 0.24), a
lag-1 autocorrelation check for independence (0.26, borderline on a 40-row test set), and a
direct correlation between `|residual|` and `|mkt_excess|` for homoscedasticity (0.57, a real
violation, the data was generated with noise that scales with market excess return on purpose).

The stretch section adds `momentum_sq` back in, since the data was generated with a genuine
quadratic momentum effect. R2 barely moves (0.368 to 0.368), a reminder that a true nonlinear
effect doesn't guarantee a visible improvement if it's small relative to the noise. The full
writeup, including what the model can and can't be trusted for, is in the notebook's
interpretation section.
