"""Sidebar controls, metric grid, and crisis bookmark buttons."""

from __future__ import annotations

import math
from datetime import date

import streamlit as st

from config.settings import (
    CORRELATION_WINDOWS,
    CRISIS_WINDOWS,
    DEFAULT_BASELINE_YEAR,
    PALETTE,
    REGIONS,
)
from src.processing.correlation import CorrelationResult

_WINDOW_LABELS: dict[int, str] = {30: "30-Day", 90: "90-Day", 360: "1-Year"}


def render_sidebar() -> tuple[str, str, int]:
    """
    Render the sidebar with region selector, chart view toggle, and baseline year picker.

    Returns:
        (region, view_mode, baseline_year) where view_mode is "Dual Axis" or "Rebased".
    """
    with st.sidebar:
        st.markdown("## Global Liquidity Tracker")
        st.markdown(
            f"<span style='font-size:0.8rem;color:{PALETTE['muted']}'>"
            "Central bank balance sheets vs equity indices</span>",
            unsafe_allow_html=True,
        )
        st.markdown("---")

        region = st.selectbox("Region", REGIONS, index=0)

        st.markdown("---")
        view_mode = st.radio("Chart View", ["Dual Axis", "Rebased"], index=0)

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

        st.markdown("<div style='flex:1'></div>", unsafe_allow_html=True)
        st.markdown("---")
        st.markdown(
            f"<div style='"
            f"text-align:center;"
            f"font-family:Fraunces,serif;"
            f"font-size:0.72rem;"
            f"color:{PALETTE['muted']};"
            f"letter-spacing:0.04em;"
            f"line-height:1.6;"
            f"padding-bottom:0.5rem"
            f"'>"
            f"Developed by<br>"
            f"<span style='font-size:0.85rem;color:{PALETTE['text']};font-style:italic'>"
            f"Jordan M. Zlatin"
            f"</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

    return region, view_mode, baseline_year


def render_crisis_buttons() -> tuple[date, date] | None:
    """
    Render a row of crisis bookmark buttons.

    Returns:
        (start, end) date tuple when a button is clicked, else None.
    """
    cols = st.columns(len(CRISIS_WINDOWS))
    clicked: tuple[date, date] | None = None
    for col, (label, (start, end)) in zip(cols, CRISIS_WINDOWS.items()):
        if col.button(label, use_container_width=True):
            clicked = (start, end)
    return clicked


def render_metric_grid(corr_result: CorrelationResult) -> None:
    """Render the latest rolling correlation values as a colored three-column grid."""
    cols = st.columns(len(CORRELATION_WINDOWS))
    for col, window in zip(cols, CORRELATION_WINDOWS):
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
            f"<div style='text-align:center;padding:0.5rem 0'>"
            f"<div class='corr-label'>{label} Corr.</div>"
            f"<div class='{css_class}'>{display}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
