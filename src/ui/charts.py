"""Dual-axis chart, rebased single-axis chart, and rolling correlation chart."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config.settings import CRISIS_WINDOWS
from src.processing.correlation import CorrelationResult
from src.processing.regimes import RegimeSegment

_WINDOW_LABELS: dict[int, str] = {30: "30-Day", 90: "90-Day", 360: "1-Year"}


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _make_window_colors(palette: dict) -> dict[int, str]:
    return {30: palette["brass"], 90: palette["verdigris"], 360: palette["muted"]}


def _make_rangeselector(palette: dict) -> dict:
    return dict(
        buttons=[
            dict(count=1, label="1Y", step="year", stepmode="backward"),
            dict(count=5, label="5Y", step="year", stepmode="backward"),
            dict(count=10, label="10Y", step="year", stepmode="backward"),
            dict(step="all", label="MAX"),
        ],
        bgcolor=palette["panel"],
        activecolor=palette["brass"],
        bordercolor=_hex_to_rgba(palette["muted"], 0.5),
        borderwidth=1,
        font=dict(family="IBM Plex Mono, monospace", size=11, color=palette["text"]),
        x=1.0,
        xanchor="right",
        y=1.12,
        yanchor="bottom",
    )


def _add_regime_shading(
    fig: go.Figure,
    segments: list[RegimeSegment],
    palette: dict,
    expansion_opacity: float,
    contraction_opacity: float,
) -> None:
    """Overlay expansion/contraction vrects behind chart traces."""
    for seg in segments:
        is_expansion = seg.label == "expansion"
        fig.add_vrect(
            x0=seg.start,
            x1=seg.end,
            fillcolor=palette["expansion"] if is_expansion else palette["contraction"],
            opacity=expansion_opacity if is_expansion else contraction_opacity,
            layer="below",
            line_width=0,
        )


def _add_endpoint(
    fig: go.Figure,
    x: pd.Timestamp,
    y: float,
    text: str,
    color: str,
    yaxis: str = "y",
) -> None:
    """Add a small dot and a floating text label at the last data point."""
    fig.add_trace(
        go.Scatter(
            x=[x],
            y=[y],
            mode="markers",
            marker=dict(color=color, size=5),
            showlegend=False,
            hoverinfo="skip",
            yaxis=yaxis,
        )
    )
    fig.add_annotation(
        x=x,
        y=y,
        xref="x",
        yref=yaxis,
        text=text,
        showarrow=False,
        xanchor="left",
        xshift=8,
        font=dict(family="IBM Plex Mono, monospace", size=11, color=color),
    )


def _add_crisis_markers(
    fig: go.Figure,
    x_min: pd.Timestamp,
    x_max: pd.Timestamp,
    palette: dict,
) -> None:
    """Draw dotted verticals at each crisis start when the view spans > 3 years."""
    span_years = (x_max - x_min).days / 365.25
    if span_years < 3:
        return
    for label, (start, _end) in CRISIS_WINDOWS.items():
        if label == "Full History":
            continue
        start_ts = pd.Timestamp(start)
        if x_min <= start_ts <= x_max:
            fig.add_vline(
                x=start_ts,
                line_width=1,
                line_dash="dot",
                line_color=_hex_to_rgba(palette["text"], 0.35),
            )
            fig.add_annotation(
                x=start_ts,
                y=1.0,
                yref="paper",
                yanchor="bottom",
                text=str(start.year),
                showarrow=False,
                font=dict(
                    family="IBM Plex Mono, monospace", size=10, color=palette["muted"]
                ),
                textangle=0,
            )


def build_dual_axis_chart(
    df: pd.DataFrame,
    cb_label: str,
    eq_label: str,
    segments: list[RegimeSegment],
    template: go.layout.Template,
    palette: dict,
    expansion_opacity: float,
    contraction_opacity: float,
    cb_axis_title: str = "Total Assets",
    eq_axis_title: str = "Index Level",
) -> go.Figure:
    """
    Build a dual y-axis chart with regime shading.

    Primary axis shows the central bank balance sheet (brass);
    secondary axis shows the equity index (verdigris).
    'cb' in df is expected pre-scaled to display units (e.g. trillions).
    """
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    _add_regime_shading(fig, segments, palette, expansion_opacity, contraction_opacity)

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["cb"],
            name=cb_label,
            line=dict(color=palette["brass"], width=2.3),
            fill="tozeroy",
            fillcolor=_hex_to_rgba(palette["brass"], 0.07),
            hovertemplate="%{x|%b %d, %Y}: %{y:,.3f}<extra>" + cb_label + "</extra>",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["eq"],
            name=eq_label,
            line=dict(color=palette["verdigris"], width=2.3),
            fill="tozeroy",
            fillcolor=_hex_to_rgba(palette["verdigris"], 0.07),
            hovertemplate="%{x|%b %d, %Y}: %{y:,.2f}<extra>" + eq_label + "</extra>",
        ),
        secondary_y=True,
    )

    last_x = df.index[-1]
    _add_endpoint(
        fig,
        last_x,
        float(df["cb"].iloc[-1]),
        f"{df['cb'].iloc[-1]:,.2f}T",
        palette["brass"],
        yaxis="y",
    )
    _add_endpoint(
        fig,
        last_x,
        float(df["eq"].iloc[-1]),
        f"{df['eq'].iloc[-1]:,.0f}",
        palette["verdigris"],
        yaxis="y2",
    )

    _add_crisis_markers(fig, df.index[0], df.index[-1], palette)

    # Pin the x-axis range to actual data + 60-day right buffer.
    # Without this Plotly auto-pads ~7% of the full span on each side (≈18 months
    # for a 22-year series), which makes the 1Y/5Y range-selector buttons anchor
    # from a future date instead of the last data point.
    x_end = df.index[-1] + pd.Timedelta(days=60)
    fig.update_layout(
        template=template,
        # Explicit (not template-level) colors: Plotly.react skips re-resolving
        # template-only changes on a reused element, so a live theme toggle
        # would otherwise leave the chart in the previous palette.
        paper_bgcolor=palette["background"],
        plot_bgcolor=palette["panel"],
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    fig.update_xaxes(
        rangeselector=_make_rangeselector(palette), range=[df.index[0], x_end]
    )
    fig.update_yaxes(title_text=cb_axis_title, secondary_y=False, rangemode="tozero")
    fig.update_yaxes(
        title_text=eq_axis_title, secondary_y=True, showgrid=False, rangemode="tozero"
    )
    return fig


def build_rebased_chart(
    df_rebased: pd.DataFrame,
    cb_label: str,
    eq_label: str,
    segments: list[RegimeSegment],
    template: go.layout.Template,
    palette: dict,
    expansion_opacity: float,
    contraction_opacity: float,
) -> go.Figure:
    """
    Build a single-axis chart with both series rebased to 100.

    Both lines carry a faint area fill to zero.
    """
    fig = go.Figure()
    _add_regime_shading(fig, segments, palette, expansion_opacity, contraction_opacity)

    fig.add_trace(
        go.Scatter(
            x=df_rebased.index,
            y=df_rebased["cb"],
            name=cb_label,
            line=dict(color=palette["brass"], width=2.3),
            fill="tozeroy",
            fillcolor=_hex_to_rgba(palette["brass"], 0.07),
            hovertemplate="%{x|%b %d, %Y}: %{y:.1f}<extra>" + cb_label + "</extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df_rebased.index,
            y=df_rebased["eq"],
            name=eq_label,
            line=dict(color=palette["verdigris"], width=2.3),
            fill="tozeroy",
            fillcolor=_hex_to_rgba(palette["verdigris"], 0.07),
            hovertemplate="%{x|%b %d, %Y}: %{y:.1f}<extra>" + eq_label + "</extra>",
        )
    )

    last_x = df_rebased.index[-1]
    _add_endpoint(
        fig,
        last_x,
        float(df_rebased["cb"].iloc[-1]),
        f"{df_rebased['cb'].iloc[-1]:,.0f}",
        palette["brass"],
    )
    _add_endpoint(
        fig,
        last_x,
        float(df_rebased["eq"].iloc[-1]),
        f"{df_rebased['eq'].iloc[-1]:,.0f}",
        palette["verdigris"],
    )

    _add_crisis_markers(fig, df_rebased.index[0], df_rebased.index[-1], palette)

    x_end = df_rebased.index[-1] + pd.Timedelta(days=60)
    fig.update_layout(
        template=template,
        # Explicit (not template-level) colors: Plotly.react skips re-resolving
        # template-only changes on a reused element, so a live theme toggle
        # would otherwise leave the chart in the previous palette.
        paper_bgcolor=palette["background"],
        plot_bgcolor=palette["panel"],
        yaxis_title="Index (Base = 100)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    fig.update_xaxes(
        rangeselector=_make_rangeselector(palette), range=[df_rebased.index[0], x_end]
    )
    return fig


def build_correlation_chart(
    corr_result: CorrelationResult,
    template: go.layout.Template,
    palette: dict,
) -> go.Figure:
    """
    Build a rolling correlation chart for 30, 90, and 360-day windows.

    30-day is muted background noise; 90-day is the visual lead; 1-year is dotted.
    """
    window_colors = _make_window_colors(palette)
    _style: dict[int, dict] = {
        30: dict(opacity=0.35, width=1, dash="solid"),
        90: dict(opacity=1.0, width=1.8, dash="solid"),
        360: dict(opacity=1.0, width=1.8, dash="dot"),
    }

    fig = go.Figure()

    fig.add_hrect(
        y0=0.5, y1=1.0, fillcolor="rgba(154,150,140,0.07)", line_width=0, layer="below"
    )
    fig.add_hrect(
        y0=-1.0,
        y1=-0.5,
        fillcolor="rgba(154,150,140,0.07)",
        line_width=0,
        layer="below",
    )

    has_data = False
    for window, series in corr_result.rolling.items():
        if series.empty:
            continue
        has_data = True
        style = _style.get(window, dict(opacity=1.0, width=1.5, dash="solid"))
        fig.add_trace(
            go.Scatter(
                x=series.index,
                y=series.values,
                name=_WINDOW_LABELS.get(window, f"{window}d"),
                line=dict(
                    color=window_colors.get(window, palette["muted"]),
                    width=style["width"],
                    dash=style["dash"],
                ),
                opacity=style["opacity"],
                hovertemplate=(
                    "%{x|%b %d, %Y}: %{y:.3f}<extra>"
                    + _WINDOW_LABELS.get(window, f"{window}d")
                    + "</extra>"
                ),
            )
        )

    if has_data:
        fig.add_hline(
            y=0,
            line_dash="dash",
            line_color=palette["muted"],
            line_width=1,
            opacity=0.5,
        )
        roll_90 = corr_result.rolling.get(90, pd.Series(dtype=float))
        if not roll_90.empty:
            _add_endpoint(
                fig,
                roll_90.index[-1],
                float(roll_90.iloc[-1]),
                f"{roll_90.iloc[-1]:+.2f}",
                window_colors[90],
            )

    fig.update_layout(
        template=template,
        # Explicit (not template-level) colors: Plotly.react skips re-resolving
        # template-only changes on a reused element, so a live theme toggle
        # would otherwise leave the chart in the previous palette.
        paper_bgcolor=palette["background"],
        plot_bgcolor=palette["panel"],
        yaxis=dict(title="Correlation", range=[-1.1, 1.1]),
        height=240,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(t=24, b=40, l=64, r=72),
    )
    return fig
