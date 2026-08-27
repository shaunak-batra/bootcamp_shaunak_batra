import pandas as pd


def get_summary_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Descriptive stats for every numeric column in df."""
    return df.describe()


def get_group_summary(df: pd.DataFrame, by: str, agg_col: str) -> pd.DataFrame:
    """Mean/sum/count of agg_col, grouped by the category column `by`."""
    return df.groupby(by)[agg_col].agg(["mean", "sum", "count"])
