# Methodology notes

Working notes on the decisions behind the code, and on the places where the
textbook version of a method had to be changed to survive contact with this data.
Written as things were found, so it reads as a record rather than a summary.

## Source papers

All four are in `docs/papers/`, gitignored. Formulas in `README.md` were checked
line by line against them.

- Bouamara, Laurent and Shi. The arXiv preprint is titled *Sequential Cauchy
  Combination Test* (arXiv:2303.13406). It has since been published as **A
  Stepwise Cauchy Combination Test for Multiple Testing Problems with Financial
  Applications**, Journal of Financial Econometrics 23(5), 2025. The method was
  renamed from "sequential" to "stepwise" between versions. Both names refer to
  the same procedure.
- Forbes and Rigobon (2002), *No Contagion, Only Interdependence*. Working paper
  version NBER w7267.
- Kritzman and Li (2010), *Skulls, Financial Turbulence, and Risk Management*.
- Kritzman, Li, Page and Rigobon (2011), *Principal Components as a Measure of
  Systemic Risk*.

Three small corrections to the README's own text, none of which change any code:

The Turbulence Index is the **squared** Mahalanobis distance, not the distance.
Kritzman and Li's note 2 says so directly. The formula in the README is right and
only the wording is loose.

The Absorption Ratio is written in the README as a ratio of eigenvalue sums and in
the source as eigenvector variance over asset variance. Those are the same number,
since the eigenvalues of a covariance matrix sum to its trace, which is the sum of
the asset variances. Setting the eigenvector count to one follows the paper's rule
of "approximately 1/5th the number of assets".

`UUP`'s fund inception is 20 February 2007, which the README has right, but its
first usable price bar is 1 March 2007. The inner-joined dataset therefore starts
1 March 2007, not late February. `DBC` is the same story: 3 February 2006
inception, first bar 6 February.

## The Fisher z-transform is mis-scaled on real returns

This is the single most important thing in these notes.

The standard result is that `arctanh(r)` for a sample correlation from `W`
observations has standard deviation `1/sqrt(W-3)`, which for `W = 60` is 0.1325.
That derivation assumes the observations inside the window are independent and
jointly normal.

Daily returns are neither. They have fat tails and volatility clustering, and both
inflate the sampling variance of a correlation estimate. Measured on the training
period by stepping through the series in non-overlapping 60-day blocks, so that no
two measurements share observations, the realised standard deviation of
`arctanh(rho)` came out at **0.284**, an inflation factor of about **2.14**.

The consequence is severe. Dividing by 0.1325 instead of 0.284 makes every test
statistic about twice as large as it should be, and a normal CDF turns that into
p-values that are far too small. A nominal 5% test rejects something closer to 30%
of the time. Roughly a quarter of all days come back with a raw p-value under 0.05
before any correction, which is not a signal, it is a broken scale.

`calibrate_baseline` measures the scale from training data and uses the measured
value. `FISHER_SD_INFLATION` in `config.py` is a documented fallback for when the
measurement itself looks unstable, which it can be: one independent observation
per window length means a nine-year training period yields only about thirty-seven
usable points, and a standard deviation estimated from thirty-seven points is not
precise.

## The test has to be one-sided

Running it two-sided produced flags concentrated in 2008 and 2012, the two calmest
and most strongly hedged years in the sample, and almost none in 2021 and 2022.
That is exactly backwards, and the reason is obvious once seen.

The baseline correlation is around -0.45. A two-sided test asks whether today's
correlation is far from that in either direction. In 2012 the correlation ran to
-0.66, which is a long way below baseline, so the test fires. But a stock-bond
correlation going more negative means the hedge is working better than usual,
which is good news.

The event this project cares about is one-directional: correlation rising toward
zero and above. `TEST_ALTERNATIVE = "greater"` in config.

## The baseline must come from a training period

Calibrating the baseline correlation on the full sample means the level being
tested against was partly set by the episodes being tested for. Training is
restricted to 2007-03-01 through 2015-12-31, which ends well before the regime
change, so everything from 2016 onward is genuinely out of sample.

Testing against a baseline of zero was also tried, on the theory that "is the
hedge gone" is the direct question. It behaves worse than either alternative,
flagging almost every day in 2008 when the correlation sat near -0.53 and almost
nothing in 2025 when it sat near +0.06. Distance from zero is not the quantity of
interest; movement away from the historical norm is.

## Multiple-testing family

The source paper corrects within a single trading day, across that day's minutes,
and reports days with at least one rejection. There is no daily equivalent given,
so the choice here is an interpretation.

A calendar quarter is used. Correcting across the entire history as one family
sounds stricter but is not a monitor at all, because no flag can be issued until
the final day of the sample is in hand. A quarter is short enough that an answer
arrives while a decision can still act on it, and long enough that the correction
has something to work with.

Empirically the choice matters less than expected. Whole-history, annual, and
quarterly families produce flag rates within about ten percentage points of each
other. Family definition is a second-order knob compared to the variance
correction above.

## Numerical care in the Cauchy combination

`tan((0.5 - p) * pi)` cannot be evaluated directly for small `p`. The argument
approaches `pi/2`, where the tangent is enormous and the floating-point
representation of `pi/2` is not exact, so the result is wrong without ever
raising an error or returning an infinity. At `p = 1e-14` the naive form is off in
the fourth significant figure; at `p = 0` it returns a large finite number that is
just the reciprocal of a rounding error.

The identity `tan(pi/2 - x) = 1/tan(x)` moves the evaluation to a small argument
where it is accurate. `_tan_transform` in `outliers.py` uses that for `p < 0.25`,
the mirrored form for `p > 0.75`, and the direct form in the middle.

Verified by simulation: the global test has empirical size 0.052 at a nominal
0.05, the stepwise version has family-wise error 0.048, and it recovers 5.00 of 5
injected signals with 0.048 false positives out of 95 nulls.

## The HMM is close to a threshold rule, and it is unstable

Fitted on the `SPY`-`TLT` rolling correlation, the two-state model separates
cleanly on paper: state means -0.507 and +0.019, separation of about 3 pooled
standard deviations, expected durations near 199 and 154 days.

Two problems sit behind those numbers.

Fitting is seed-dependent. Across twenty random starts a meaningful fraction
collapse to a degenerate solution with both state means on the pooled mean, which
is one Gaussian pretending to be two. Every collapsed fit reports
`converged = True`, so that flag cannot be used to detect the failure.
`fit_regime_hmm` takes the best of twenty restarts by log-likelihood and reports
separation explicitly so a collapse is visible.

And the model is nearly a threshold rule. A hysteresis rule with two parameters,
entering above -0.244 and leaving below -0.304, agrees with the fitted HMM on
about 98% of days. What the HMM actually buys is stability of the label: 26 flips
across the sample against 39 for hysteresis and 81 for a single fixed threshold.
That is worth something for a monitor a person has to act on, but it is a much
smaller claim than "the model found the regimes".

Model selection does not support more than two states. BIC decreases monotonically
from one state through six without ever turning, which means it is quantising a
smooth continuum rather than finding discrete regimes. No `K > 2` result is
reported anywhere.

Refitting on an expanding window and decoding only forward relabels about 22% of
days relative to the full-sample fit, concentrated in the early years. A
full-sample decode describes history; it is not evidence the model would have
called it that way at the time.

## What the data says about the project's premise

The README states that correlations across this basket moved toward one in the
second half of 2008, in March 2020, and through much of 2022. Checked directly,
that holds for 2022 only.

| window | mean pairwise corr | SPY-TLT |
|---|---|---|
| full sample | -0.051 | -0.277 |
| 2008 GFC | -0.134 | -0.535 |
| COVID 2020 | +0.020 | -0.522 |
| 2022 | -0.010 | -0.015 |

In 2008 the average pairwise correlation sits 1.6 standard deviations **below** its
full-sample mean, and the stock-bond correlation is twice as negative as normal.
The reason is structural rather than a data problem: the basket holds
flight-to-quality assets on purpose, and in a flight to quality they rally while
equities fall, which drives their correlation more negative during exactly the
windows labelled as breakdowns.

Measured by Diversification Ratio the same picture holds. 2008 scores +0.08
standard deviations, meaning diversification worked slightly better than usual.
COVID scores -0.51 and 2022 -0.69.

The three stress measures are also close to mutually uncorrelated across the
sample (average correlation against Absorption Ratio -0.098, against Turbulence
+0.085; Absorption Ratio against Turbulence +0.104). They are not three views of
one quantity, so they are reported separately rather than blended into a single
score.

The consequence for the evaluation is direct and is not hidden in the notebook:
detection precision against the labelled windows is 0.042 and recall 0.052, with a
block-bootstrap interval on F1 that includes zero. The monitor is being graded on
two events where the phenomenon it detects did not occur.

Where it does fire is 2021 onward, with 232 days of lead before the 2022 window
opens, and the Forbes-Rigobon check confirms that move is real: variance rose
thirteen-fold between the calm 2017 window and 2022, yet only about 5% of the
correlation change is attributable to that volatility increase.

## Open items

The ADF test rejects the unit root on the rolling correlation series at p = 0.004,
which cuts against the framing of correlation regimes as persistent random walks.
The result is hard to lean on either way, because ADF applied to a series built
from overlapping windows is testing something mechanically autocorrelated by
construction. Worth revisiting with a non-overlapping series.

The exposure backtest avoids no drawdown, because `SPY`'s worst drawdown is
2008-2009 and the monitor is correctly silent then. It costs about 21 percentage
points of cumulative return over the sample. On the current labelling that is the
honest result.
