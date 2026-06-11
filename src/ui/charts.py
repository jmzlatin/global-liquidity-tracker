"""Dual-axis chart, rebased single-axis chart, and rolling correlation chart."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config.settings import CONTRACTION_OPACITY, EXPANSION_OPACITY, PALETTE
from src.processing.correlation import CorrelationResult
from src.processing.regimes import RegimeSegment

_WINDOW_LABELS: dict[int, str] = {30: "30-Day", 90: "90-Day", 360: "1-Year"}
_WINDOW_COLORS: dict[int, str] = {
    30: PALETTE["brass"],
    90: PALETTE["verdigris"],
    360: PALETTE["muted"],
}


def _add_regime_shading(fig: go.Figure, segments: list[RegimeSegment]) -> None:
    """Overlay expansion/contraction vrects behind chart traces."""
    for seg in segments:
        is_expansion = seg.label == "expansion"
        fig.add_vrect(
            x0=seg.start,
            x1=seg.end,
            fillcolor=PALETTE["expansion"] if is_expansion else PALETTE["contraction"],
            opacity=EXPANSION_OPACITY if is_expansion else CONTRACTION_OPACITY,
            layer="below",
            line_width=0,
        )


def build_dual_axis_chart(
    df: pd.DataFrame,
    cb_label: str,
    eq_label: str,
    segments: list[RegimeSegment],
    template: go.layout.Template,
    cb_axis_title: str = "Total Assets",
    eq_axis_title: str = "Index Level",
) -> go.Figure:
    """
    Build a dual y-axis chart with regime shading.

    Primary axis shows the central bank balance sheet (brass);
    secondary axis shows the equity index (verdigris).

    Args:
        df: DataFrame with 'cb' and 'eq' columns and a daily DatetimeIndex.
            'cb' is expected pre-scaled to its display unit (e.g. trillions).
        cb_label: Display name for the central bank series (legend + hover).
        eq_label: Display name for the equity series (legend + hover).
        segments: Regime segments for background shading.
        template: Plotly layout template.
        cb_axis_title: Primary y-axis title, including the display unit.
        eq_axis_title: Secondary y-axis title for the equity index.

    Returns:
        Plotly Figure.
    """
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    _add_regime_shading(fig, segments)

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["cb"],
            name=cb_label,
            line=dict(color=PALETTE["brass"], width=2),
            hovertemplate="%{x|%Y-%m-%d}: %{y:,.3f}<extra>" + cb_label + "</extra>",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["eq"],
            name=eq_label,
            line=dict(color=PALETTE["verdigris"], width=2),
            hovertemplate="%{x|%Y-%m-%d}: %{y:,.2f}<extra>" + eq_label + "</extra>",
        ),
        secondary_y=True,
    )

    fig.update_layout(
        template=template,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_yaxes(
        title_text=cb_axis_title,
        secondary_y=False,
        gridcolor=PALETTE["muted"],
        gridwidth=0.5,
        tickfont=dict(family="IBM Plex Mono, monospace", color=PALETTE["muted"], size=11),
    )
    fig.update_yaxes(
        title_text=eq_axis_title,
        secondary_y=True,
        gridcolor=PALETTE["muted"],
        gridwidth=0.5,
        tickfont=dict(family="IBM Plex Mono, monospace", color=PALETTE["muted"], size=11),
        showgrid=False,
    )
    return fig


def build_rebased_chart(
    df_rebased: pd.DataFrame,
    cb_label: str,
    eq_label: str,
    segments: list[RegimeSegment],
    template: go.layout.Template,
) -> go.Figure:
    """
    Build a single-axis chart with both series rebased to 100.

    Args:
        df_rebased: DataFrame with 'cb' and 'eq' columns rebased to 100.
        cb_label: Display name for the central bank series.
        eq_label: Display name for the equity series.
        segments: Regime segments for background shading.
        template: Plotly layout template.

    Returns:
        Plotly Figure.
    """
    fig = go.Figure()
    _add_regime_shading(fig, segments)

    fig.add_trace(go.Scatter(
        x=df_rebased.index,
        y=df_rebased["cb"],
        name=cb_label,
        line=dict(color=PALETTE["brass"], width=2),
        hovertemplate="%{x|%Y-%m-%d}: %{y:.1f}<extra>" + cb_label + "</extra>",
    ))
    fig.add_trace(go.Scatter(
        x=df_rebased.index,
        y=df_rebased["eq"],
        name=eq_label,
        line=dict(color=PALETTE["verdigris"], width=2),
        hovertemplate="%{x|%Y-%m-%d}: %{y:.1f}<extra>" + eq_label + "</extra>",
    ))

    fig.update_layout(
        template=template,
        yaxis_title="Index (Base = 100)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def build_correlation_chart(
    corr_result: CorrelationResult,
    template: go.layout.Template,
) -> go.Figure:
    """
    Build a line chart of rolling correlations for the 30, 90, and 360-day windows.

    Args:
        corr_result: CorrelationResult with rolling series per window.
        template: Plotly layout template.

    Returns:
        Plotly Figure. Empty figure if there is no correlation data.
    """
    fig = go.Figure()

    has_data = False
    for window, series in corr_result.rolling.items():
        if series.empty:
            continue
        has_data = True
        fig.add_trace(go.Scatter(
            x=series.index,
            y=series.values,
            name=_WINDOW_LABELS.get(window, f"{window}d"),
            line=dict(color=_WINDOW_COLORS.get(window, PALETTE["muted"]), width=1.5),
            hovertemplate=(
                "%{x|%Y-%m-%d}: %{y:.3f}<extra>"
                + _WINDOW_LABELS.get(window, f"{window}d")
                + "</extra>"
            ),
        ))

    if has_data:
        fig.add_hline(
            y=0, line_dash="dash", line_color=PALETTE["muted"], line_width=1, opacity=0.5
        )

    fig.update_layout(
        template=template,
        yaxis=dict(title="Correlation", range=[-1.1, 1.1]),
        height=200,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=24, b=40, l=64, r=48),
    )
    return fig
