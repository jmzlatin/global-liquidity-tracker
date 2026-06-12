"""Unit tests for src/processing/correlation.py."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from src.processing.correlation import CorrelationResult, compute_correlation


def _series(values: list[float] | np.ndarray, start: str = "2020-01-01") -> pd.Series:
    idx = pd.date_range(start, periods=len(values), freq="D")
    return pd.Series(np.asarray(values, dtype=float), index=idx)


def _random_walk(n: int, seed: int = 42) -> np.ndarray:
    rng = np.random.default_rng(seed)
    pcts = rng.normal(0, 0.01, n)
    return np.cumprod(1 + pcts) * 100


# ── basic shape and types ─────────────────────────────────────────────────────


def test_returns_correlation_result():
    s = _series(_random_walk(400))
    result = compute_correlation(s, s)
    assert isinstance(result, CorrelationResult)


def test_result_keys_match_windows():
    s = _series(_random_walk(400))
    windows = [30, 90]
    result = compute_correlation(s, s, windows=windows)
    assert set(result.latest.keys()) == {30, 90}
    assert set(result.rolling.keys()) == {30, 90}


# ── empty / insufficient data ─────────────────────────────────────────────────


def test_empty_series_returns_nan_latest():
    cb = _series([])
    eq = _series([])
    result = compute_correlation(cb, eq, windows=[30])
    assert math.isnan(result.latest[30])


def test_empty_series_returns_empty_rolling():
    cb = _series([])
    eq = _series([])
    result = compute_correlation(cb, eq, windows=[30])
    assert result.rolling[30].empty


def test_insufficient_data_returns_nan():
    # 10 observations < 30-day window → latest should be NaN
    cb = _series(list(range(10)))
    eq = _series(list(range(10)))
    result = compute_correlation(cb, eq, windows=[30])
    assert math.isnan(result.latest[30])


# ── known-value cases ─────────────────────────────────────────────────────────


def test_identical_series_correlation_is_one():
    values = _random_walk(400)
    cb = _series(values)
    eq = _series(values)
    result = compute_correlation(cb, eq, windows=[30])
    assert result.latest[30] == pytest.approx(1.0, abs=1e-9)


def test_anti_correlated_series_correlation_is_minus_one():
    # Construct cb and eq whose pct_changes are r and -r respectively.
    # pct_change of cumprod(1+r) is exactly r, so corr = -1.
    rng = np.random.default_rng(7)
    r = rng.normal(0, 0.01, 400)
    cb = _series(np.cumprod(1 + r) * 100)
    eq = _series(np.cumprod(1 - r) * 100)
    result = compute_correlation(cb, eq, windows=[30])
    assert result.latest[30] == pytest.approx(-1.0, abs=1e-9)


def test_rolling_series_length_consistent_with_data():
    values = _random_walk(400)
    cb = _series(values)
    eq = _series(values)
    result = compute_correlation(cb, eq, windows=[30, 90])
    # Longer window → fewer valid rolling values
    assert len(result.rolling[30]) >= len(result.rolling[90])


def test_latest_matches_tail_of_rolling():
    values = _random_walk(400)
    cb = _series(values)
    eq = _series(values)
    result = compute_correlation(cb, eq, windows=[30])
    assert result.latest[30] == pytest.approx(result.rolling[30].iloc[-1], abs=1e-12)
