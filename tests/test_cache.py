"""Unit tests for src/ingestion/cache.py."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

from src.ingestion.cache import get_series


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_series(name: str = "TEST") -> pd.Series:
    idx = pd.date_range("2020-01-01", periods=5, freq="D")
    return pd.Series([1.0, 2.0, 3.0, 4.0, 5.0], index=idx, name=name)


def _ts(hours_ago: float = 0) -> str:
    return (datetime.now(tz=timezone.utc) - timedelta(hours=hours_ago)).isoformat()


def _seed_cache(cache_dir: Path, series_id: str, series: pd.Series, fetched_at: str) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    safe_name = series_id.replace("^", "").replace("/", "_")
    series.to_csv(cache_dir / f"{safe_name}.csv", header=True)
    with open(cache_dir / "manifest.json", "w") as f:
        json.dump({series_id: {"fetched_at": fetched_at}}, f)


# ── fresh cache ───────────────────────────────────────────────────────────────

def test_fresh_cache_skips_fetcher(tmp_path):
    cache_dir = tmp_path / "cache"
    expected = _make_series()
    _seed_cache(cache_dir, "TEST", expected, _ts(hours_ago=1))

    called = False

    def fetcher() -> pd.Series:
        nonlocal called
        called = True
        return expected

    result, stale = get_series("TEST", fetcher, cache_dir=str(cache_dir))
    assert not called
    assert not stale
    assert list(result.values) == pytest.approx(list(expected.values))


# ── stale cache ───────────────────────────────────────────────────────────────

def test_stale_cache_calls_fetcher(tmp_path):
    cache_dir = tmp_path / "cache"
    expected = _make_series()
    _seed_cache(cache_dir, "TEST", expected, _ts(hours_ago=25))

    called = False

    def fetcher() -> pd.Series:
        nonlocal called
        called = True
        return expected

    result, stale = get_series("TEST", fetcher, cache_dir=str(cache_dir))
    assert called
    assert not stale


def test_stale_fetch_failure_returns_stale_flag(tmp_path):
    cache_dir = tmp_path / "cache"
    expected = _make_series()
    _seed_cache(cache_dir, "TEST", expected, _ts(hours_ago=25))

    def fetcher() -> pd.Series:
        raise ConnectionError("network down")

    result, stale = get_series("TEST", fetcher, cache_dir=str(cache_dir))
    assert stale
    assert list(result.values) == pytest.approx(list(expected.values))


# ── missing cache ─────────────────────────────────────────────────────────────

def test_missing_cache_calls_fetcher(tmp_path):
    cache_dir = tmp_path / "cache"
    expected = _make_series()

    def fetcher() -> pd.Series:
        return expected

    result, stale = get_series("TEST", fetcher, cache_dir=str(cache_dir))
    assert not stale
    assert list(result.values) == pytest.approx(list(expected.values))


def test_missing_cache_writes_csv(tmp_path):
    cache_dir = tmp_path / "cache"
    expected = _make_series()

    get_series("TEST", lambda: expected, cache_dir=str(cache_dir))
    assert (cache_dir / "TEST.csv").exists()


def test_missing_cache_writes_manifest(tmp_path):
    cache_dir = tmp_path / "cache"
    expected = _make_series()

    get_series("TEST", lambda: expected, cache_dir=str(cache_dir))
    manifest = json.loads((cache_dir / "manifest.json").read_text())
    assert "fetched_at" in manifest["TEST"]


def test_no_cache_and_fetch_failure_raises(tmp_path):
    cache_dir = tmp_path / "cache"

    def fetcher() -> pd.Series:
        raise ConnectionError("network down")

    with pytest.raises(RuntimeError, match="No cached data"):
        get_series("MISSING", fetcher, cache_dir=str(cache_dir))


# ── ticker sanitization ───────────────────────────────────────────────────────

def test_caret_ticker_sanitized_to_safe_filename(tmp_path):
    cache_dir = tmp_path / "cache"
    expected = _make_series("^GSPC")

    get_series("^GSPC", lambda: expected, cache_dir=str(cache_dir))
    assert (cache_dir / "GSPC.csv").exists()
    assert not (cache_dir / "^GSPC.csv").exists()
