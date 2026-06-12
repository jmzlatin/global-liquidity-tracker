"""Tests for src/processing/summary.py."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from src.processing.correlation import CorrelationResult
from src.processing.regimes import RegimeSegment
from src.processing.summary import KpiSummary, build_insight, compute_summary


def _make_df(n_days: int = 200) -> pd.DataFrame:
    """Synthetic daily DataFrame with known values."""
    idx = pd.date_range("2020-01-01", periods=n_days, freq="D")
    cb = pd.Series(np.linspace(5.0, 8.0, n_days), index=idx)
    eq = pd.Series(np.linspace(3000.0, 4200.0, n_days), index=idx)
    return pd.DataFrame({"cb": cb, "eq": eq})


def _make_segments(df: pd.DataFrame, label: str = "expansion") -> list[RegimeSegment]:
    return [RegimeSegment(start=df.index[0], end=df.index[-1], label=label)]


def _make_corr(corr_90: float = 0.72) -> CorrelationResult:
    return CorrelationResult(
        latest={30: 0.5, 90: corr_90, 360: 0.6},
        rolling={
            30: pd.Series(dtype=float),
            90: pd.Series(dtype=float),
            360: pd.Series(dtype=float),
        },
    )


def test_latest_values() -> None:
    df = _make_df(200)
    summary = compute_summary(df, _make_segments(df), _make_corr())
    assert summary.cb_latest == pytest.approx(float(df["cb"].iloc[-1]))
    assert summary.eq_latest == pytest.approx(float(df["eq"].iloc[-1]))


def test_90d_change_known_value() -> None:
    df = _make_df(200)
    summary = compute_summary(df, _make_segments(df), _make_corr())
    # cb goes from 5.0 to 8.0 over 200 days linearly
    # 90 days before end ≈ day 110, value ≈ 5 + (110/199)*3 ≈ 6.658
    assert not math.isnan(summary.cb_change_90d_pct)
    assert summary.cb_change_90d_pct > 0  # upward slope → positive change


def test_regime_fields() -> None:
    df = _make_df(200)
    segs = [RegimeSegment(start=df.index[50], end=df.index[-1], label="contraction")]
    summary = compute_summary(df, segs, _make_corr())
    assert summary.regime_label == "contraction"
    assert summary.regime_since == df.index[50]


def test_corr_90d() -> None:
    df = _make_df(200)
    summary = compute_summary(df, _make_segments(df), _make_corr(0.88))
    assert summary.corr_90d == pytest.approx(0.88)


def test_nan_corr() -> None:
    df = _make_df(200)
    corr = _make_corr(float("nan"))
    summary = compute_summary(df, _make_segments(df), corr)
    assert math.isnan(summary.corr_90d)


def test_short_frame_under_90_days() -> None:
    """Frame shorter than 90 days should fall back to first row, not NaN."""
    df = _make_df(30)
    summary = compute_summary(df, _make_segments(df), _make_corr())
    # With <90 days, asof returns NaN and we fall back to first row
    assert not math.isnan(summary.cb_change_90d_pct)


def test_empty_segments() -> None:
    df = _make_df(200)
    summary = compute_summary(df, [], _make_corr())
    assert summary.regime_label == "expansion"
    assert summary.regime_since == df.index[0]


def test_build_insight_expansion() -> None:
    df = _make_df(200)
    summary = compute_summary(df, _make_segments(df, "expansion"), _make_corr())
    text = build_insight(summary, "United States", "S&P 500")
    assert "Fed" in text
    assert "expansion" in text
    assert "S&P 500" in text


def test_build_insight_contraction() -> None:
    df = _make_df(200)
    summary = compute_summary(df, _make_segments(df, "contraction"), _make_corr())
    text = build_insight(summary, "Eurozone", "Euro Stoxx 50")
    assert "ECB" in text
    assert "contraction" in text


def test_build_insight_nan_deltas() -> None:
    """NaN deltas should produce a sentence without the parenthetical or 'moved X%'."""
    df = _make_df(5)  # very short → NaN deltas possible
    summary = KpiSummary(
        cb_latest=7.0,
        cb_change_90d_pct=float("nan"),
        eq_latest=4000.0,
        eq_change_90d_pct=float("nan"),
        regime_label="expansion",
        regime_since=df.index[0],
        corr_90d=float("nan"),
    )
    text = build_insight(summary, "Japan", "Nikkei 225")
    assert "BOJ" in text
    assert "%" not in text  # no delta parenthetical
