# Reports

## Format chosen: written report (`final_report.md`)

**Audience:** a portfolio manager or risk committee reviewing a scenario analysis before a
capital allocation decision, someone who wants the numbers and the reasoning behind them, but
isn't going to run the notebook themselves.

**Why this format fits.** A slide deck compresses too much of the "why" out of a result like
this one, and the whole point of the report is that the assumption behind a number (how missing
data gets filled, how outliers get handled) changes the number by as much as switching
scenarios entirely. A written report can hold the number, the chart, and the caveat about that
number in the same place, in order, which a slide's bullet-point format resists. A dashboard
would be the right call if this needed to be explored interactively across many scenarios;
here, three fixed scenarios and a fixed sensitivity table don't need that.

`final_report.md` has the executive summary, three charts (`images/`), assumptions and risks,
the sensitivity table, and a decision-implications section, in that order.
