# Homework 05: Data Storage

## Data Storage

**Folder structure.** `data/raw/` holds the CSV export straight from the DataFrame, unedited.
`data/processed/` holds the same data as Parquet, the format later stages read from once the raw
export has been through any cleaning.

**Formats and why.** CSV for `data/raw/` because it is plain text, easy to open and diff, and
matches what most raw sources hand you. Parquet for `data/processed/` because it keeps column
dtypes on reload (a CSV round trip turns a datetime column back into a string unless you remember
to `parse_dates` every time), and it is smaller and faster to read for anything downstream.

**How the code reads and writes.** `DATA_DIR_RAW` and `DATA_DIR_PROCESSED` come from `.env` and
resolve to `data/raw` and `data/processed`. `write_df(df, path)` and `read_df(path)` look at the
file suffix to decide CSV or Parquet, create any missing parent directories before writing, and
raise a `RuntimeError` with a plain-language message if a Parquet engine isn't installed instead
of letting the raw exception through.

**Validation.** `validate_loaded()` reloads each saved file and checks the shape matches the
original DataFrame and that `date`/`price` kept their expected dtypes after the round trip. Both
CSV and Parquet passed.
