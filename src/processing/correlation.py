"""Rolling correlation between central bank balance sheet and equity index returns."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from config.settings import CORRELATION_WINDOWS


@dataclass
class CorrelationResult:
    """Latest rolling correlation values and the full rolling series."""

    latest: dict[int, float]         # window → latest correlation coefficient
    rolling: dict[int, pd.Series]    # window → full rolling correlation series


def compute_correlation(
    cb_series: pd.Series,
    eq_series: pd.Series,
    windows: list[int] = CORRELATION_WINDOWS,
) -> CorrelationResult:
    """
    Compute rolling Pearson correlation between percent changes of two series.

    Both series are aligned on a common daily index before computing returns.
    NaN values introduced by forward-fill stretches are dropped from the
    rolling inputs so flat constant segments do not produce noise correlations.

    Args:
        cb_series: Central bank balance sheet Series (daily, already forward-filled).
        eq_series: Equity close price Series (daily, already forward-filled).
        windows: List of rolling window sizes in days.

    Returns:
        CorrelationResult with latest coefficient per window and the full
        rolling Series per window. Latest values are NaN if insufficient data.
    """
    combined = pd.DataFrame({"cb": cb_series, "eq": eq_series}).dropna()

    if combined.empty:
        empty: dict[int, float] = {w: float("nan") for w in windows}
        empty_series: dict[int, pd.Series] = {
            w: pd.Series(dtype=float) for w in windows
        }
        return CorrelationResult(latest=empty, rolling=empty_series)

    cb_ret = combined["cb"].pct_change()
    eq_ret = combined["eq"].pct_change()

    latest: dict[int, float] = {}
    rolling: dict[int, pd.Series] = {}

    for w in windows:
        roll = cb_ret.rolling(w).corr(eq_ret).dropna()
        rolling[w] = roll
        latest[w] = float(roll.iloc[-1]) if not roll.empty else float("nan")

    return CorrelationResult(latest=latest, rolling=rolling)
