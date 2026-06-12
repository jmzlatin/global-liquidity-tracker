"""Compute KPI summary values from the processed dataframe and analysis results."""

from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

from config.settings import BANK_SHORT_NAMES
from src.processing.correlation import CorrelationResult
from src.processing.regimes import RegimeSegment


@dataclass(frozen=True)
class KpiSummary:
    cb_latest: float
    cb_change_90d_pct: float
    eq_latest: float
    eq_change_90d_pct: float
    regime_label: str  # "expansion" or "contraction"
    regime_since: pd.Timestamp
    corr_90d: float


def _pct_change_vs_90d(series: pd.Series) -> float:
    """Return pct change from 90 calendar days ago to latest. NaN if insufficient data."""
    if series.empty:
        return float("nan")
    target = series.index[-1] - pd.Timedelta(days=90)
    prior = series.asof(target)
    if pd.isna(prior):
        prior = float(series.iloc[0])
    latest = float(series.iloc[-1])
    if prior == 0 or math.isnan(prior):
        return float("nan")
    return (latest - prior) / abs(prior) * 100.0


def compute_summary(
    df: pd.DataFrame,
    segments: list[RegimeSegment],
    corr: CorrelationResult,
) -> KpiSummary:
    """
    Compute headline KPI values from the merged dataframe and analysis results.

    Args:
        df: DataFrame with 'cb' (in display units, e.g. trillions) and 'eq' columns.
        segments: Regime segments from compute_regimes.
        corr: Correlation result from compute_correlation.

    Returns:
        KpiSummary frozen dataclass with all headline fields.
    """
    cb_latest = float(df["cb"].iloc[-1])
    eq_latest = float(df["eq"].iloc[-1])
    cb_change_90d_pct = _pct_change_vs_90d(df["cb"])
    eq_change_90d_pct = _pct_change_vs_90d(df["eq"])

    if segments:
        last_seg = segments[-1]
        regime_label = last_seg.label
        regime_since = last_seg.start
    else:
        regime_label = "expansion"
        regime_since = df.index[0]

    corr_90d = corr.latest.get(90, float("nan"))

    return KpiSummary(
        cb_latest=cb_latest,
        cb_change_90d_pct=cb_change_90d_pct,
        eq_latest=eq_latest,
        eq_change_90d_pct=eq_change_90d_pct,
        regime_label=regime_label,
        regime_since=regime_since,
        corr_90d=corr_90d,
    )


def build_insight(summary: KpiSummary, region: str, eq_label: str) -> str:
    """Build a one-sentence market commentary from KPI values."""
    bank = BANK_SHORT_NAMES.get(region, "Central Bank")
    since = summary.regime_since.strftime("%b %Y")

    cb_paren = (
        f" ({summary.cb_change_90d_pct:+.1f}% over 90 days)"
        if not math.isnan(summary.cb_change_90d_pct)
        else ""
    )
    eq_move = (
        f"moved {summary.eq_change_90d_pct:+.1f}%"
        if not math.isnan(summary.eq_change_90d_pct)
        else "moved"
    )

    return (
        f"The {bank} balance sheet has been in {summary.regime_label} since {since}"
        f"{cb_paren}, while the {eq_label} {eq_move} over the same stretch."
    )
