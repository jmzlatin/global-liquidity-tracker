"""Local 24-hour disk cache for FRED and equity series — CSV per series + manifest.json."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import pandas as pd

from config.settings import CACHE_DIR, CACHE_TTL_HOURS, MANIFEST_FILENAME

logger = logging.getLogger(__name__)


def _manifest_path(root: Path) -> Path:
    return root / MANIFEST_FILENAME


def _csv_path(root: Path, series_id: str) -> Path:
    safe_name = series_id.replace("^", "").replace("/", "_")
    return root / f"{safe_name}.csv"


def _load_manifest(root: Path) -> dict:
    path = _manifest_path(root)
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def _save_manifest(root: Path, manifest: dict) -> None:
    with open(_manifest_path(root), "w") as f:
        json.dump(manifest, f, indent=2)


def _is_fresh(fetched_at: str | None) -> bool:
    """Return True if fetched_at ISO timestamp is under CACHE_TTL_HOURS old."""
    if not fetched_at:
        return False
    then = datetime.fromisoformat(fetched_at)
    if then.tzinfo is None:
        then = then.replace(tzinfo=timezone.utc)
    age_hours = (datetime.now(tz=timezone.utc) - then).total_seconds() / 3600
    return age_hours < CACHE_TTL_HOURS


def _read_csv(csv: Path, series_id: str) -> pd.Series:
    df = pd.read_csv(csv, index_col=0, parse_dates=True)
    series = df.iloc[:, 0]
    series.index = pd.DatetimeIndex(series.index).tz_localize(None)
    series.name = series_id
    return series


def get_series(
    series_id: str,
    fetcher: Callable[[], pd.Series],
    cache_dir: str = CACHE_DIR,
) -> tuple[pd.Series, bool]:
    """
    Return a cached series when fresh; fetch and cache it when stale or missing.

    Falls back to stale cache if the live fetch raises any exception.

    Args:
        series_id: Unique key used for the CSV filename and manifest entry.
        fetcher: Zero-argument callable that fetches and returns a fresh pd.Series.
        cache_dir: Root directory for cache files. Created if absent.

    Returns:
        Tuple of (series, stale_warning). stale_warning is True only when data
        came from a stale cache because a live fetch failed.

    Raises:
        RuntimeError: if there is no cached fallback and the live fetch failed.
    """
    root = Path(cache_dir)
    root.mkdir(parents=True, exist_ok=True)

    manifest = _load_manifest(root)
    csv = _csv_path(root, series_id)
    fetched_at = manifest.get(series_id, {}).get("fetched_at")

    if _is_fresh(fetched_at) and csv.exists():
        return _read_csv(csv, series_id), False

    try:
        series = fetcher()
        series.to_csv(csv, header=True)
        manifest.setdefault(series_id, {})["fetched_at"] = (
            datetime.now(tz=timezone.utc).isoformat()
        )
        _save_manifest(root, manifest)
        return series, False
    except Exception as exc:
        logger.warning(
            "Fetch failed for %s (%s); falling back to stale cache.", series_id, exc
        )
        if csv.exists():
            return _read_csv(csv, series_id), True
        raise RuntimeError(
            f"No cached data for {series_id!r} and live fetch failed: {exc}"
        ) from exc
