# Homework 08: Exploratory Data Analysis

Full EDA on a synthetic customer-transactions dataset (`date`, `region`, `age`, `income`,
`transactions`, `spend`, 160 rows with injected missingness and outliers): numeric and
categorical profiling, distribution and relationship plots, a time-series read on `spend`, and
a correlation matrix.

`src/eda.py` holds `eda_summary(df)`, extracted from the lecture and extended to flag columns
worth attention before feature engineering (high missingness, near-zero variance, one category
dominating). On this dataset it comes back clean, no flags, which is itself worth noting since
the notebook's own profiling found two real outlier rows in `transactions` that a
missingness or variance check alone would not catch.

Top 3 insights, assumptions, risks, and next steps for stage 09 are all written out at the end
of the notebook.
