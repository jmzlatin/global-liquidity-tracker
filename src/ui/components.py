"""Sidebar controls, hero header, KPI cards, metric grid, and crisis bookmark buttons."""

from __future__ import annotations

import math
from datetime import date, datetime, timezone

import pandas as pd
import streamlit as st

from config.settings import (
    CORRELATION_WINDOWS,
    CRISIS_WINDOWS,
    DEFAULT_BASELINE_YEAR,
    FRED_SERIES,
    EQUITY_TICKERS,
    REGIONS,
)
from src.processing.correlation import CorrelationResult
from src.processing.summary import KpiSummary

_WINDOW_LABELS: dict[int, str] = {30: "30-Day", 90: "90-Day", 360: "1-Year"}


# ── Sidebar ───────────────────────────────────────────────────────────────────


def render_sidebar(manifest: dict | None, palette: dict) -> tuple[str, str, int]:
    """
    Render the sidebar with brand, region selector, chart view toggle, theme toggle,
    freshness block, and credit.

    Returns:
        (region, view_mode, baseline_year) where view_mode is "Dual Axis" or "Rebased".
    """
    with st.sidebar:
        st.markdown(
            "<div class='brand'>"
            "<span class='brand-glyph'>◆</span> GLOBAL LIQUIDITY TRACKER"
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<span style='font-size:0.8rem;color:{palette['muted']};font-family:IBM Plex Sans,sans-serif'>"
            "Central bank balance sheets vs equity indices</span>",
            unsafe_allow_html=True,
        )
        st.markdown("<div class='sidebar-rule'></div>", unsafe_allow_html=True)

        region = st.selectbox("Region", REGIONS, index=0)

        st.markdown("<div class='sidebar-rule'></div>", unsafe_allow_html=True)
        view_mode = st.radio(
            "Chart View", ["Dual Axis", "Rebased"], index=0, horizontal=True
        )

        baseline_year: int = DEFAULT_BASELINE_YEAR
        if view_mode == "Rebased":
            baseline_year = int(
                st.number_input(
                    "Baseline Year",
                    min_value=2004,
                    max_value=date.today().year - 1,
                    value=DEFAULT_BASELINE_YEAR,
                    step=1,
                )
            )

        st.radio("Theme", ["Paper", "Terminal"], key="theme", horizontal=True)

        # Data freshness block
        if manifest:
            st.markdown("<div class='sidebar-rule'></div>", unsafe_allow_html=True)
            render_freshness(manifest)

        st.markdown("<div style='flex:1'></div>", unsafe_allow_html=True)
        st.markdown("<div class='sidebar-rule'></div>", unsafe_allow_html=True)
        st.markdown(
            f"<div style='"
            f"text-align:center;"
            f"font-family:Fraunces,serif;"
            f"font-size:0.72rem;"
            f"color:{palette['muted']};"
            f"letter-spacing:0.04em;"
            f"line-height:1.6;"
            f"padding-bottom:0.5rem"
            f"'>"
            f"Developed by<br>"
            f"<span style='font-size:0.85rem;color:{palette['text']};font-style:italic'>"
            f"Jordan M. Zlatin"
            f"</span><br>"
            f"<a href='https://github.com/jmzlatin/global-liquidity-tracker' "
            f"style='color:{palette['muted']};font-size:0.72rem;text-decoration:none;'"
            f" onmouseover=\"this.style.color='{palette['brass']}'\" "
            f" onmouseout=\"this.style.color='{palette['muted']}'\">View source ↗</a>"
            f"</div>",
            unsafe_allow_html=True,
        )

    return region, view_mode, baseline_year


def render_freshness(manifest: dict) -> None:
    """Render per-series data freshness timestamps as mono lines."""
    now = datetime.now(tz=timezone.utc)
    lines: list[str] = []
    for series_id, info in manifest.items():
        fetched_at = info.get("fetched_at", "")
        if fetched_at:
            then = datetime.fromisoformat(fetched_at)
            if then.tzinfo is None:
                then = then.replace(tzinfo=timezone.utc)
            age_min = (now - then).total_seconds() / 60
            if age_min < 60:
                age_str = f"{int(age_min)}m ago"
            elif age_min < 1440:
                age_str = f"{int(age_min / 60)}h ago"
            else:
                age_str = f"{int(age_min / 1440)}d ago"
        else:
            age_str = "unknown"
        lines.append(f"{series_id} · {age_str}")
    st.markdown(
        "<div class='freshness-block'>" + "<br>".join(lines) + "</div>",
        unsafe_allow_html=True,
    )


# ── Hero ──────────────────────────────────────────────────────────────────────


def render_hero(
    region: str,
    cb_label: str,
    eq_label: str,
    currency: str,
    date_start: date,
    date_end: date,
) -> None:
    """Render the eyebrow / title / sub-line hero block at the top of the page."""
    sub_text = (
        f"Central bank assets in trillions {currency} · {eq_label} index level · "
        f"{date_start.strftime('%b %d, %Y')} – {date_end.strftime('%b %d, %Y')}"
    )
    st.markdown(
        f"<div class='hero-block'>"
        f"<div class='hero-eyebrow'>"
        f"<span class='pulse-dot'></span>LIQUIDITY · {region.upper()}"
        f"</div>"
        f"<div class='hero-title'>"
        f"{cb_label} <span class='hero-vs'>vs</span> {eq_label}"
        f"</div>"
        f"<div class='hero-sub'>{sub_text}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


# ── KPI cards ─────────────────────────────────────────────────────────────────


def _delta_html(pct: float) -> str:
    """Format a percent-change delta as HTML with directional arrow and sign color."""
    if math.isnan(pct):
        return "<span class='kpi-delta-neutral'>—</span>"
    arrow = "▲" if pct >= 0 else "▼"
    cls = "kpi-delta-pos" if pct >= 0 else "kpi-delta-neg"
    return f"<span class='{cls}'>{arrow} {abs(pct):.1f}% (90d)</span>"


_SPARK_POINTS = 90  # trailing observations shown, matching the 90d delta window


def _sparkline_svg(
    series: pd.Series | None, color: str, width: int = 108, height: int = 38
) -> str:
    """Build an inline SVG sparkline with a draw-in line, gradient fill, and end dot."""
    if series is None:
        return ""
    s = series.dropna().iloc[-_SPARK_POINTS:]
    if len(s) < 2:
        return ""
    vals = s.to_list()
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1.0
    n = len(vals)
    pts = [
        (1 + i * (width - 2) / (n - 1), height - 3 - (v - lo) / span * (height - 6))
        for i, v in enumerate(vals)
    ]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"1,{height - 1} {line} {width - 1},{height - 1}"
    gid = f"sg{color.lstrip('#')}"
    end_x, end_y = pts[-1]
    return (
        f"<span class='kpi-spark'>"
        f"<svg width='{width}' height='{height}' viewBox='0 0 {width} {height}'>"
        f"<defs><linearGradient id='{gid}' x1='0' y1='0' x2='0' y2='1'>"
        f"<stop offset='0%' stop-color='{color}' stop-opacity='0.25'/>"
        f"<stop offset='100%' stop-color='{color}' stop-opacity='0'/>"
        f"</linearGradient></defs>"
        f"<polygon class='spark-fill' points='{area}' fill='url(#{gid})'/>"
        f"<polyline class='spark-line' points='{line}' fill='none' stroke='{color}'"
        f" stroke-width='1.6' stroke-linejoin='round' stroke-linecap='round'/>"
        f"<circle class='spark-dot' cx='{end_x:.1f}' cy='{end_y:.1f}' r='2.2'"
        f" fill='{color}'/>"
        f"</svg></span>"
    )


def render_kpi_row(
    summary: KpiSummary,
    currency: str,
    eq_label: str,
    palette: dict,
    cb_spark: pd.Series | None = None,
    eq_spark: pd.Series | None = None,
    corr_spark: pd.Series | None = None,
) -> None:
    """Render four KPI cards: balance sheet, equity, regime, correlation.

    Optional series render as trailing-90-observation sparklines inside the cards.
    """
    cols = st.columns(4)

    # Card 1: Balance sheet
    cols[0].markdown(
        f"<div class='kpi-card accent-brass stagger-1'>"
        f"<div class='kpi-label'>Balance Sheet</div>"
        f"<div class='kpi-flex'><div>"
        f"<div class='kpi-value'>{summary.cb_latest:,.2f}T"
        f" <span class='kpi-unit'>{currency}</span></div>"
        f"{_delta_html(summary.cb_change_90d_pct)}"
        f"</div>{_sparkline_svg(cb_spark, palette['brass'])}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # Card 2: Equity index
    cols[1].markdown(
        f"<div class='kpi-card accent-verdigris stagger-2'>"
        f"<div class='kpi-label'>{eq_label}</div>"
        f"<div class='kpi-flex'><div>"
        f"<div class='kpi-value'>{summary.eq_latest:,.0f}</div>"
        f"{_delta_html(summary.eq_change_90d_pct)}"
        f"</div>{_sparkline_svg(eq_spark, palette['verdigris'])}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # Card 3: Regime
    is_expansion = summary.regime_label == "expansion"
    pill_cls = "regime-pill-expansion" if is_expansion else "regime-pill-contraction"
    accent_cls = "accent-expansion" if is_expansion else "accent-contraction"
    pill_text = summary.regime_label.upper()
    since_str = summary.regime_since.strftime("%b %Y")
    cols[2].markdown(
        f"<div class='kpi-card {accent_cls} stagger-3'>"
        f"<div class='kpi-label'>Regime</div>"
        f"<span class='regime-pill {pill_cls}'>"
        f"<span class='pill-dot'></span>{pill_text}</span>"
        f"<div class='kpi-delta-neutral' style='margin-top:0.3rem'>since {since_str}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # Card 4: 90-day correlation
    if math.isnan(summary.corr_90d):
        corr_html = "<span class='corr-neutral'>N/A</span>"
    elif summary.corr_90d >= 0:
        corr_html = f"<span class='corr-positive'>{summary.corr_90d:+.3f}</span>"
    else:
        corr_html = f"<span class='corr-negative'>{summary.corr_90d:+.3f}</span>"

    cols[3].markdown(
        f"<div class='kpi-card accent-muted stagger-4'>"
        f"<div class='kpi-label'>90-Day Correlation</div>"
        f"<div class='kpi-flex'><div>"
        f"<div class='kpi-value'>{corr_html}</div>"
        f"<span class='kpi-delta-neutral'>r(CB, {eq_label})</span>"
        f"</div>{_sparkline_svg(corr_spark, palette['muted'])}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


# ── Insight ───────────────────────────────────────────────────────────────────


def render_insight(text: str) -> None:
    """Render the auto-generated market insight as a brass-bordered callout."""
    st.markdown(
        f"<div class='insight-callout'>{text}</div>",
        unsafe_allow_html=True,
    )


# ── Crisis buttons ────────────────────────────────────────────────────────────


def render_crisis_buttons() -> tuple[date, date] | None:
    """
    Render a row of crisis bookmark buttons with active-state highlighting
    and a Custom date popover.

    Returns:
        (start, end) date tuple when a button or Apply is clicked, else None.
    """
    if "active_window" not in st.session_state:
        st.session_state["active_window"] = "Full History"

    st.markdown(
        "<div class='time-window-label'>TIME WINDOW</div>", unsafe_allow_html=True
    )

    n_cols = len(CRISIS_WINDOWS) + 1  # +1 for custom popover
    cols = st.columns(n_cols)
    clicked: tuple[date, date] | None = None

    for col, (label, (start, end)) in zip(
        cols[: len(CRISIS_WINDOWS)], CRISIS_WINDOWS.items()
    ):
        is_active = st.session_state["active_window"] == label
        btn_type = "primary" if is_active else "secondary"
        if col.button(label, type=btn_type, use_container_width=True):
            st.session_state["active_window"] = label
            clicked = (start, end)

    # Custom date range popover
    with cols[-1]:
        with st.popover("Custom…", use_container_width=True):
            from_val = st.session_state.get("date_start", date(2015, 1, 1))
            to_val = st.session_state.get("date_end", date.today())
            from_date = st.date_input("From", value=from_val)
            to_date = st.date_input("To", value=to_val)
            if st.button("Apply", key="_custom_apply"):
                if from_date >= to_date:
                    st.caption("'From' must be earlier than 'To'")
                else:
                    st.session_state["active_window"] = "Custom"
                    clicked = (from_date, to_date)

    return clicked


# ── Regime key ────────────────────────────────────────────────────────────────


def render_regime_key(palette: dict) -> None:
    """Render a right-aligned legend for the regime shading bands."""
    st.markdown(
        "<div class='regime-key'>"
        f"<span style='color:{palette['expansion']}'>■</span> Expansion &nbsp;&nbsp;"
        f"<span style='color:{palette['contraction']}'>■</span> Contraction"
        "</div>",
        unsafe_allow_html=True,
    )


# ── Section header ────────────────────────────────────────────────────────────


def render_section_header(title: str, subtitle: str) -> None:
    """Render a ruled two-line section header in Fraunces."""
    st.markdown(
        f"<div class='section-header'>"
        f"<div class='section-title'>{title}</div>"
        f"<div class='section-subtitle'>{subtitle}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


# ── Correlation metric grid ───────────────────────────────────────────────────


def _sign_bar_html(value: float) -> str:
    """Build a 4px horizontal sign bar centered at 50%."""
    if math.isnan(value):
        return "<div class='sign-bar-track'><div class='sign-bar-center'></div></div>"
    fill_pct = abs(value) * 50
    if value >= 0:
        fill = f"<div class='sign-bar-fill-pos' style='width:{fill_pct:.1f}%'></div>"
    else:
        fill = f"<div class='sign-bar-fill-neg' style='width:{fill_pct:.1f}%'></div>"
    return (
        f"<div class='sign-bar-track'><div class='sign-bar-center'></div>{fill}</div>"
    )


def render_metric_grid(corr_result: CorrelationResult) -> None:
    """Render the latest rolling correlation values as styled KPI cards with sign bars."""
    cols = st.columns(len(CORRELATION_WINDOWS))
    for i, (col, window) in enumerate(zip(cols, CORRELATION_WINDOWS), start=1):
        value = corr_result.latest.get(window, float("nan"))
        label = _WINDOW_LABELS.get(window, f"{window}d")

        if math.isnan(value):
            css_class = "corr-neutral"
            display = "N/A"
        elif value >= 0:
            css_class = "corr-positive"
            display = f"{value:+.3f}"
        else:
            css_class = "corr-negative"
            display = f"{value:+.3f}"

        col.markdown(
            f"<div class='kpi-card stagger-{i}' style='text-align:center'>"
            f"<div class='corr-label'>{label} Corr.</div>"
            f"<div class='{css_class}'>{display}</div>"
            f"{_sign_bar_html(value)}"
            f"</div>",
            unsafe_allow_html=True,
        )


# ── Footer ────────────────────────────────────────────────────────────────────


def render_footer(region: str) -> None:
    """Render a source-and-disclaimer footer with FRED and Yahoo Finance links."""
    series_id = FRED_SERIES[region]["series_id"]
    ticker = EQUITY_TICKERS[region]["ticker"]
    fred_url = f"https://fred.stlouisfed.org/series/{series_id}"
    yf_url = f"https://finance.yahoo.com/quote/{ticker}"
    st.markdown(
        f"<div class='footer'>"
        f"Data: <a href='{fred_url}' target='_blank'>FRED ({series_id})</a>"
        f" · <a href='{yf_url}' target='_blank'>Yahoo Finance ({ticker})</a>"
        f" · Cached 24h · Not investment advice"
        f"</div>",
        unsafe_allow_html=True,
    )
