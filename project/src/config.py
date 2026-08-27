"""Configuration constants for the Cross-Asset Diversification Breakdown Monitor.

Values here match what is documented in project/README.md. Nothing in this file
computes anything; it only names the parameters everything else reads.
"""

TICKERS = ["SPY", "TLT", "GLD", "DBC", "UUP"]

# UUP is the youngest of the five tickers (fund inception 2007-02-20). Because raw
# prices are aligned on an inner join across all five, this sets the usable start of
# the dataset, not 2006 -- see project/README.md, Data section. Note the first bar
# that actually clears the inner join is 2007-03-01; the fund inception date is kept
# here as the request start and the join decides the real beginning.
START_DATE = "2007-02-20"

WINDOW = 60  # trading days, rolling correlation window

Z_THRESHOLD = 2.0  # stress-score z-score alert threshold

CRISIS_WINDOWS = {
    "gfc": ("2008-09-01", "2009-03-31"),
    "covid": ("2020-02-20", "2020-04-30"),
    "rate_shock_2022": ("2022-01-01", "2022-10-31"),
}

# --- Absorption Ratio -------------------------------------------------------
# Kritzman, Li, Page & Rigobon (2011) fix the eigenvector count at "approximately
# 1/5th the number of assets". With five assets that is exactly one.
AR_N_EIGENVECTORS = 1

# --- Statistical testing ----------------------------------------------------
# Everything below exists because the naive version of this test is mis-calibrated
# on real data. See docs/methodology_notes.md for the measurements behind each value.

# The Fisher z-transform assumes iid returns inside the window. Real returns have
# fat tails and volatility clustering, so the realised standard deviation of
# arctanh(rho_t) is about twice the theoretical 1/sqrt(W-3). Measured on a stable
# stretch (2013-2019) it came out at 2.05x. Without this correction a nominal 5%
# test has a true size near 30%.
FISHER_SD_INFLATION = 2.05

# The correlation baseline is calibrated on this period only, never on the full
# sample. Using the full sample would test the flags against data that helped set
# the threshold they are compared to.
TRAIN_START = "2007-03-01"
TRAIN_END = "2015-12-31"

# The question is one-sided: correlation rising toward zero (hedge failing) is the
# event of interest. A correlation falling further below baseline is the hedge
# working better than usual and must not raise an alarm.
TEST_ALTERNATIVE = "greater"

# Multiple-testing family. The source paper corrects within one trading day over
# that day's minutes. The daily analogue used here is one calendar quarter, which
# keeps the family small enough to stay powerful and short enough that a flag is
# not delayed by more than a quarter.
SCC_FAMILY = "quarter"
SCC_ALPHA = 0.01

# --- Storage ----------------------------------------------------------------
RAW_DIR = "data/raw"
PROCESSED_DIR = "data/processed"
