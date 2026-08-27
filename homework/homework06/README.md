# Homework 06: Data Preprocessing

## Cleaning Strategy

Three functions in `src/cleaning.py`, applied in this order:

1. `drop_missing(df, threshold=0.5)` drops any column missing more than half its values.
   In this dataset that's `extra_data`, missing in 5 of 7 rows.
2. `fill_missing_median(df, columns)` fills the remaining gaps in `age`, `income`, and `score`
   with each column's median. Median instead of mean because a small sample like this is easily
   skewed by one or two outliers.
3. `normalize_data(df, columns)` min-max scales `income` and `score` to 0-1, so a column
   measured in tens of thousands doesn't dominate a column measured in tenths just because of
   its units.

`zipcode` and `city` are left as is. They have no missing values, and neither a median fill nor
normalization means anything for a zip code or a city name.

The full reasoning and the tradeoff of dropping `extra_data` outright (versus keeping a
missingness flag) is in the notebook, right after the cleaning is applied.
