"""Unit tests for src/processing/normalize.py."""

from __future__ import annotations

import pandas as pd
import pytest

from src.processing.normalize import merge_and_ffill, rebase_to_100


def _weekly(start: str, periods: int, values: list[float]) -> pd.Series:
    return pd.Series(values, index=pd.date_range(start, periods=periods, freq="W"))


def _daily(start: str, n: int) -> pd.Series:
    return pd.Series(
        range(n), index=pd.date_range(start, periods=n, freq="D"), dtype=float
    )


def test_merge_and_ffill_columns_present():
    cb = _weekly("2020-01-01", 4, [100.0, 110.0, 120.0, 130.0])
    eq = _daily("2020-01-01", 28)
    df = merge_and_ffill(cb, eq)
    assert list(df.columns) == ["cb", "eq"]


def test_merge_and_ffill_no_nans():
    cb = _weekly("2020-01-01", 4, [100.0, 110.0, 120.0, 130.0])
    eq = _daily("2020-01-01", 28)
    df = merge_and_ffill(cb, eq)
    assert df.notna().all().all()


def test_merge_and_ffill_forward_fills_weekly_gaps():
    cb = _weekly("2020-01-01", 4, [100.0, 110.0, 120.0, 130.0])
    eq = _daily("2020-01-01", 28)
    df = merge_and_ffill(cb, eq)
    first_cb_date = cb.index[0]
    # Days 1-6 after the first weekly print carry that value forward
    for delta in range(1, 6):
        day = first_cb_date + pd.Timedelta(days=delta)
        if day in df.index:
            assert df.loc[day, "cb"] == 100.0


def test_merge_and_ffill_drops_leading_nans():
    # cb starts 7 days after eq — rows before cb's first observation should be gone
    cb = pd.Series([200.0, 210.0], index=pd.to_datetime(["2020-01-08", "2020-01-15"]))
    eq = _daily("2020-01-01", 20)
    df = merge_and_ffill(cb, eq)
    assert df.notna().all().all()
    assert df.index[0] >= pd.Timestamp("2020-01-08")


def test_rebase_to_100_anchor_is_100():
    idx = pd.date_range("2015-01-01", periods=100, freq="D")
    df = pd.DataFrame(
        {"cb": range(1, 101), "eq": range(100, 200)}, index=idx, dtype=float
    )
    rebased = rebase_to_100(df, 2015)
    assert rebased["cb"].iloc[0] == pytest.approx(100.0)
    assert rebased["eq"].iloc[0] == pytest.approx(100.0)


def test_rebase_to_100_second_value():
    # cb starts at 1, increments by 1 → rebased value at idx[1] should be 200
    idx = pd.date_range("2015-01-01", periods=10, freq="D")
    df = pd.DataFrame({"cb": range(1, 11), "eq": range(1, 11)}, index=idx, dtype=float)
    rebased = rebase_to_100(df, 2015)
    assert rebased["cb"].iloc[1] == pytest.approx(200.0)


def test_rebase_to_100_missing_year_raises():
    idx = pd.date_range("2015-01-01", periods=10, freq="D")
    df = pd.DataFrame({"cb": range(1, 11), "eq": range(1, 11)}, index=idx, dtype=float)
    with pytest.raises(ValueError, match="No data found in baseline year"):
        rebase_to_100(df, 2020)


def test_rebase_to_100_zero_anchor_raises():
    idx = pd.date_range("2015-01-01", periods=5, freq="D")
    df = pd.DataFrame({"cb": [0.0, 1.0, 2.0, 3.0, 4.0], "eq": [1.0] * 5}, index=idx)
    with pytest.raises(ValueError, match="NaN or zero"):
        rebase_to_100(df, 2015)
