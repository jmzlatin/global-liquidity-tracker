"""Unit tests for src/processing/regimes.py."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.processing.regimes import RegimeSegment, _rolling_slope, compute_regimes


def _series(values: list[float] | np.ndarray, start: str = "2020-01-01") -> pd.Series:
    idx = pd.date_range(start, periods=len(values), freq="D")
    return pd.Series(values, index=idx, dtype=float)


# ── _rolling_slope ────────────────────────────────────────────────────────────


def test_rolling_slope_positive():
    # Linear increase: slope = 1.0
    s = _series(np.arange(10, dtype=float))
    slopes = _rolling_slope(s, window=5)
    assert slopes.dropna().iloc[-1] == pytest.approx(1.0)


def test_rolling_slope_negative():
    # Linear decrease: slope = -1.0
    s = _series(np.arange(10, 0, -1, dtype=float))
    slopes = _rolling_slope(s, window=5)
    assert slopes.dropna().iloc[-1] == pytest.approx(-1.0)


def test_rolling_slope_flat():
    s = _series([5.0] * 20)
    slopes = _rolling_slope(s, window=5)
    assert slopes.dropna().iloc[-1] == pytest.approx(0.0)


def test_rolling_slope_leading_nans():
    s = _series(np.arange(10, dtype=float))
    slopes = _rolling_slope(s, window=5)
    # First window-1 entries must be NaN
    assert slopes.iloc[:4].isna().all()


# ── compute_regimes ───────────────────────────────────────────────────────────


def test_compute_regimes_empty():
    assert compute_regimes(pd.Series([], dtype=float)) == []


def test_compute_regimes_too_short_for_window():
    # Fewer points than the window → no valid slopes → empty list
    s = _series([1.0, 2.0, 3.0])
    assert compute_regimes(s, window=10) == []


def test_compute_regimes_expansion_only():
    s = _series(np.arange(200, dtype=float))
    segments = compute_regimes(s)
    assert len(segments) >= 1
    assert all(seg.label == "expansion" for seg in segments)


def test_compute_regimes_contraction_only():
    s = _series(np.arange(200, 0, -1, dtype=float))
    segments = compute_regimes(s)
    assert len(segments) >= 1
    assert all(seg.label == "contraction" for seg in segments)


def test_compute_regimes_both_labels_present():
    # First 150 up, next 150 down
    values = list(np.arange(150)) + list(np.arange(150, 0, -1))
    s = _series(values)
    labels = {seg.label for seg in compute_regimes(s)}
    assert "expansion" in labels
    assert "contraction" in labels


def test_compute_regimes_contiguous():
    # Each segment's end equals the next segment's start — no gaps
    values = list(np.arange(150)) + list(np.arange(150, 0, -1))
    s = _series(values)
    segments = compute_regimes(s)
    for i in range(len(segments) - 1):
        assert segments[i].end == segments[i + 1].start


def test_compute_regimes_result_type():
    s = _series(np.arange(200, dtype=float))
    segments = compute_regimes(s)
    for seg in segments:
        assert isinstance(seg, RegimeSegment)
        assert seg.label in ("expansion", "contraction")
        assert seg.start <= seg.end
