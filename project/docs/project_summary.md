# Project summary

A non-technical account of what this project set out to do, what it found, and what
should and should not be relied on. Written for someone who will not run the code.

## The problem

Almost every multi-asset portfolio rests on a claim that is empirical rather than
guaranteed: that stocks, government bonds, gold, commodities and the dollar do not all
fall at once. Sizing a book, setting risk limits, and choosing a hedge all depend on that
claim holding. When it stops holding, a portfolio built to spread risk starts behaving
like a single concentrated position, and it does so at exactly the moment that hurts most.

The question this project asks is narrow on purpose: is the diversification a portfolio
depends on still working, and if it stops, can that be detected while a decision can still
be made about it.

## How it works

The monitor tracks five exchange-traded funds standing in for five asset classes. Every
trading day it measures how closely each pair of them has moved together over the previous
sixty days, and compresses those measurements into a handful of summary numbers. The most
useful one is simply how much the basket's actual volatility is reduced by holding the five
things together rather than one of them alone.

It then asks whether today's reading is far enough from the historical norm to count as a
real change rather than ordinary fluctuation. That is a statistical test, and because the
same test runs every single day for nineteen years, it has to account for the fact that
running any test thousands of times will produce some alarming-looking results by chance
alone.

Finally it classifies each day into one of two regimes, one where the diversifying
relationships hold and one where they are impaired, and reports that alongside the evidence
behind it rather than as a bare signal.

## What it found

**The stock-bond hedge inverted around 2021 and has not recovered.** Over 2008 to 2020,
equities and long Treasuries moved in opposite directions reliably, with an average
correlation of about -0.43. From 2021 onward that average is about +0.08. They now tend to
move the same way. The transition was gradual rather than a single event: the relationship
weakened through 2021, reached zero in 2022, and has been positive since.

This is the central finding, and it matters because the bond allocation in a conventional
portfolio is there specifically to offset equity losses. For the past five years it has not
been doing that.

**The change is genuine, not a side effect of turbulent markets.** There is a well-known
statistical trap here: correlations rise automatically when volatility rises, even when
nothing about the underlying relationship has changed. Volatility in 2022 was more than
thirteen times its calm-period level, so this had to be checked. After correcting for it,
about 95% of the correlation change remains. It is a real change in how the two assets
relate to each other, and it will not reverse simply because markets calm down.

**The monitor stayed silent through the 2008 financial crisis and the March 2020 crash,
and that is correct.** This is the most counterintuitive result and the most important one
to understand. In both of those crises the hedge worked better than usual, not worse.
Equities fell, investors fled into Treasuries and the dollar, and those holdings rallied.
Diversification did its job. The project originally assumed those events were examples of
diversification breaking down, and the data says plainly that they were not.

## What this means in practice

A portfolio sized on the correlation between stocks and bonds observed before 2021 is
carrying more risk than its own risk model reports. The correlation matrix underpinning
that sizing should be re-estimated on recent data.

Bonds should be treated as a return-generating holding rather than as a hedge until the
relationship turns negative again. Whatever diversification the book currently has is
coming from somewhere other than the equity-bond pair.

And the monitor should be read for what it measures. It answers whether diversifying
relationships are intact. It does not forecast losses, and the two questions came apart
visibly in 2008 and 2020.

## What not to rely on

**Three labelled events is a very thin basis for any claim about accuracy.** Two of the
three turned out not to be examples of the thing being detected, which leaves one. No
confident statement about how well this would catch the next episode is supportable.

**The regime classifier is barely better than a simple threshold.** A rule that says
"elevated when the correlation rises above roughly -0.24" agrees with the fitted model on
98% of days. The model's genuine contribution is that it changes its mind less often, not
that it sees something a simpler rule misses.

**The historical regime chart flatters the model.** It was fitted using the whole history
including the future of any given day. Refitted properly so that each day is classified
using only what was known at the time, about a fifth of days change label. The chart
describes the past well; it is not proof the monitor would have said the same thing live.

**The funds are stand-ins for asset classes, not the asset classes themselves,** and they
can drift from what they represent during precisely the stress the monitor exists to catch.

## Where it could go next

The most valuable extension is straightforward. The statistical machinery already works on
any pair of assets, but the reporting layer currently focuses on stocks and bonds. Running
the same testing procedure across all ten pairs would catch a breakdown anywhere in the
basket with the same discipline, rather than only in the pair that has been examined most
closely.

Beyond that, the honest next step is more evidence. One clear episode in nineteen years is
enough to describe what happened and not enough to make confident claims about detection
skill. Applying the same method to other baskets and other markets would establish whether
what was found here generalises or is specific to this set of five holdings.
