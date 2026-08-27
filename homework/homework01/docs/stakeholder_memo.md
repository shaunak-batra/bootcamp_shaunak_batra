# Stakeholder Memo

**To:** Portfolio Manager / Head of Risk, multi-asset desk
**From:** Risk Analytics
**Re:** Weekly diversification-breakdown monitor

This memo introduces a weekly monitor built to answer one question: is the correlation
structure this portfolio's diversification depends on still holding, or has it started
to break down.

In 2008, in March 2020, and again in 2022, the five asset classes this portfolio spreads
across (equities, Treasuries, gold, commodities, and the dollar) moved together instead
of offsetting each other, and the portfolio's realized risk ended up close to what a
single leveraged equity position would have produced. The monitor tracks rolling
correlation across a five-ETF proxy basket for exactly this pattern, and produces a
weekly read: normal, or breaking down.

When the read crosses into breaking down, that is the trigger to review gross exposure,
not a standing recommendation to act automatically. The report behind the flag will
always show the current stress score, its recent trend, and which specific pair of
assets is driving the reading, so the call gets made on the evidence, not on a single
number alone.
