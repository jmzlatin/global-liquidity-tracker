"""Merge, forward-fill, and rebase central bank and equity series onto a shared daily index."""

from __future__ import annotations

import pandas as pd


def merge_and_ffill(cb_series: pd.Series, eq_series: pd.Series) -> pd.DataFrame:
    """
    Align two series onto a daily DatetimeIndex spanning their union of dates.

    Both series are reindexed to daily frequency and forward-filled so weekly
    and monthly central bank prints carry forward to each trading day.

    Args:
        cb_series: Central bank balance sheet series (weekly or monthly).
        eq_series: Equity close price series (daily, trading days only).

    Returns:
        DataFrame with columns ['cb', 'eq'], daily DatetimeIndex, no leading NaN
        rows (rows before the first valid value in each column are dropped).
    """
    daily_index = pd.date_range(
        start=min(cb_series.index.min(), eq_series.index.min()),
        end=max(cb_series.index.max(), eq_series.index.max()),
        freq="D",
    )

    df = pd.DataFrame(
        {
            "cb": cb_series.reindex(daily_index),
            "eq": eq_series.reindex(daily_index),
        }
    )

    df["cb"] = df["cb"].ffill()
    df["eq"] = df["eq"].ffill()

    # Drop leading rows where either column has no data yet
    df = df.dropna()
    return df


def rebase_to_100(df: pd.DataFrame, baseline_year: int) -> pd.DataFrame:
    """
    Rebase both columns so each equals 100 at the first observation of baseline_year.

    Args:
        df: DataFrame with 'cb' and 'eq' columns and a daily DatetimeIndex.
        baseline_year: Year to anchor at 100.

    Returns:
        New DataFrame with rebased values. Columns keep the same names.
        Raises ValueError if no data exists in the baseline year for either column.
    """
    year_mask = df.index.year == baseline_year
    baseline_rows = df.loc[year_mask].dropna()

    if baseline_rows.empty:
        raise ValueError(f"No data found in baseline year {baseline_year}")

    anchor = baseline_rows.iloc[0]

    for col in ("cb", "eq"):
        if pd.isna(anchor[col]) or anchor[col] == 0:
            raise ValueError(
                f"Baseline anchor for '{col}' in {baseline_year} is NaN or zero"
            )

    return df.div(anchor) * 100
