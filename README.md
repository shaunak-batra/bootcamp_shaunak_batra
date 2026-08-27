# Bootcamp Repository

Coursework and project repository for FRE 5040, submitted by Shaunak Batra.

## About this repository

This repository holds two things: the weekly homework exercises assigned throughout the
course, and one cumulative project carried across the whole semester. They are built to
the same standard but serve different purposes. Homework is graded practice on data the
course provides; the project is applied to a dataset and problem chosen at the start of
the semester and extended stage by stage using the same techniques practiced in
homework.

## Folder Structure

- **homework/** - All homework contributions will be submitted here.
- **project/** - All project contributions will be submitted here.
- **class_materials/** - Local storage for class materials. Never pushed to GitHub.

## Homework Folder Rules

- Each homework will be in its own subfolder (`homework00`, `homework01`, etc.), numbered to match the stage
- Include all required files for grading.

## Class Materials Rules

- Each stage's handouts go in their own subfolder, named exactly as the course folder, e.g. `class_materials/stage01_problem-framing-and-scoping/`.
- Run lecture notebooks in place from that folder.
- Copy a homework starter into `homework/homeworkNN/` before working on it.

## Project Folder Rules

- Keep project files organized and clearly named.
- The project folder structure is set up in Stage 02.

## The project: Cross-Asset Diversification Breakdown Monitor

Multi-asset portfolios are built on the premise that stocks, bonds, gold, commodities,
and currencies do not all fall together, so that when one holding drops the others
cushion the loss. That premise periodically fails: in 2008, in March 2020, and again in
2022, correlations across these asset classes moved toward one at the same time
volatility spiked, and portfolios built to be diversified instead behaved like a single
leveraged position.

This project builds a monitor for exactly that failure. It pulls daily prices for a
five-asset proxy basket (`SPY`, `TLT`, `GLD`, `DBC`, `UUP`), tracks their rolling
correlation, and produces a weekly regime classification, normal or breaking down,
using a two-state Hidden Markov Model fit on an engineered stress score (average
correlation, the Absorption Ratio of Kritzman, Li, Page & Rigobon 2011, and the
Turbulence Index of Kritzman & Li 2010). Breakdown flags are tested for statistical
validity using the sequential Cauchy combination test of Bouamara, Laurent & Shi
(2023), a method built to control false alarms in exactly this situation: the same
test run repeatedly, day after day, on serially correlated statistics.

The full problem framing, methodology with formulas, assumptions, known risks, and
references are documented in [`project/README.md`](project/README.md).
