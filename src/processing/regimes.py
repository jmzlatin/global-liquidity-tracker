"""Rolling regime detection: classify central bank balance sheet trend as expansion or contraction."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from config.settings import REGIME_WINDOW_DAYS


@dataclass
class RegimeSegment:
    """A contiguous period of consistent expansion or contraction."""

    start: pd.Timestamp
    end: pd.Timestamp
    label: str  # "expansion" or "contraction"


def _rolling_slope(series: pd.Series, window: int) -> pd.Series:
    """
    Compute the OLS slope over a rolling window.

    Uses the slope of a simple linear regression (x = 0..window-1, y = values).
    Returns a float Series with the same index as *series*; early entries are NaN.
    """
    x = np.arange(window, dtype=float)
    x_mean = x.mean()
    x_var = ((x - x_mean) ** 2).sum()

    def _slope(y: np.ndarray) -> float:
        if np.isnan(y).any():
            return float("nan")
        return float(((x - x_mean) * (y - y.mean())).sum() / x_var)

    return series.rolling(window).apply(_slope, raw=True)


def compute_regimes(
    cb_series: pd.Series,
    window: int = REGIME_WINDOW_DAYS,
) -> list[RegimeSegment]:
    """
    Classify the central bank series into expansion and contraction segments.

    Fits a rolling OLS slope over *window* days. Positive slope → expansion,
    negative → contraction. Consecutive same-sign days are collapsed into one
    contiguous RegimeSegment.

    Args:
        cb_series: Daily central bank balance sheet Series with DatetimeIndex.
        window: Rolling window in days for slope calculation.

    Returns:
        List of RegimeSegment covering the full range of dates with a slope
        value (i.e. from index[window-1] onward). No gaps, no overlaps.
    """
    if cb_series.empty:
        return []

    slopes = _rolling_slope(cb_series.ffill(), window)
    slope_valid = slopes.dropna()

    if slope_valid.empty:
        return []

    signs = pd.Series(
        np.where(slope_valid >= 0, "expansion", "contraction"),
        index=slope_valid.index,
    )

    segments: list[RegimeSegment] = []
    seg_start = signs.index[0]
    current_label = signs.iloc[0]

    for date, label in signs.iloc[1:].items():
        if label != current_label:
            segments.append(
                RegimeSegment(start=seg_start, end=date, label=current_label)
            )
            seg_start = date
            current_label = label

    segments.append(
        RegimeSegment(start=seg_start, end=signs.index[-1], label=current_label)
    )
    return segments
