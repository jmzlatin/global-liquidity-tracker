"""Global Market Liquidity & Central Bank Tracker — Streamlit entry point."""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from config.settings import EQUITY_TICKERS, FRED_SERIES, MILLIONS_PER_TRILLION, PALETTE
from src.ingestion.cache import get_series
from src.ingestion.equity_client import fetch_equity
from src.ingestion.fred_client import fetch_series
from src.processing.correlation import compute_correlation
from src.processing.normalize import merge_and_ffill, rebase_to_100
from src.processing.regimes import compute_regimes
from src.ui.charts import build_correlation_chart, build_dual_axis_chart, build_rebased_chart
from src.ui.components import render_crisis_buttons, render_metric_grid, render_sidebar
from src.ui.theme import get_plotly_template, inject_css

st.set_page_config(
    page_title="Global Liquidity Tracker",
    page_icon="📊",
    layout="wide",
)

inject_css()
plotly_template = get_plotly_template()

region, view_mode, baseline_year = render_sidebar()

# Session state holds the active date range; crisis buttons can override it.
if "date_start" not in st.session_state:
    st.session_state["date_start"] = date(2004, 1, 1)
if "date_end" not in st.session_state:
    st.session_state["date_end"] = date.today()

with st.expander("What is this?", expanded=False):
    st.markdown(
        """
**Global liquidity** is the total amount of money sloshing around the world's financial system.
The biggest driver is central banks: when a central bank like the Federal Reserve buys bonds,
it creates new money and its balance sheet grows — that's *expansion*. When it sells bonds or
lets them mature, money is destroyed and the balance sheet shrinks — that's *contraction*.

More liquidity tends to push asset prices up because investors have more cash to put to work.
Less liquidity tends to pull prices down as that cash gets withdrawn.

**This tracker plots each central bank's total assets alongside its regional stock index** so you
can see that relationship play out over time. The dual-axis view keeps both series on the same
chart with independent scales. Switch to *Rebased* to normalize both to 100 at a common start
date for a cleaner percentage-change comparison.

The **rolling correlation panel** below the main chart shows how tightly the two series have
moved together over the last 30, 90, and 360 days. A positive number means they've been rising
and falling together; a negative number means they've been moving in opposite directions.
        """,
        unsafe_allow_html=False,
    )

crisis_range = render_crisis_buttons()
if crisis_range:
    st.session_state["date_start"], st.session_state["date_end"] = crisis_range

date_start: date = st.session_state["date_start"]
date_end: date = st.session_state["date_end"]


@st.cache_data(ttl=86400, show_spinner=False)
def _load_cb(region: str) -> tuple[pd.Series, bool]:
    series_id = FRED_SERIES[region]["series_id"]
    return get_series(series_id, lambda: fetch_series(series_id))


@st.cache_data(ttl=86400, show_spinner=False)
def _load_eq(region: str) -> tuple[pd.Series, bool]:
    ticker = EQUITY_TICKERS[region]["ticker"]
    return get_series(ticker, lambda: fetch_equity(ticker))


with st.spinner("Loading data…"):
    cb_series, cb_stale = _load_cb(region)
    eq_series, eq_stale = _load_eq(region)

if cb_stale or eq_stale:
    st.warning("One or more series is served from a stale cache — the live fetch failed.")

cb_filtered = cb_series.loc[str(date_start) : str(date_end)]
eq_filtered = eq_series.loc[str(date_start) : str(date_end)]

if cb_filtered.empty or eq_filtered.empty:
    st.error("No data available for the selected date range.")
    st.stop()

df = merge_and_ffill(cb_filtered, eq_filtered)
if df.empty:
    st.error("No overlapping data for the selected region and date range.")
    st.stop()

segments = compute_regimes(df["cb"])
corr_result = compute_correlation(df["cb"], df["eq"])

# FRED reports balance sheets in millions; convert to trillions for display.
# Safe to do before plotting: regimes (slope sign), correlation (pct_change),
# and rebase-to-100 are all scale-invariant.
df["cb"] = df["cb"] / MILLIONS_PER_TRILLION

cb_label = FRED_SERIES[region]["label"]
eq_label = EQUITY_TICKERS[region]["label"]
currency = FRED_SERIES[region]["currency"]
cb_axis_title = f"Total Assets (Trillions {currency})"
eq_axis_title = f"{eq_label} (Index)"

st.markdown(f"## {region} — {cb_label} vs {eq_label}")
st.markdown(
    f"<span style='font-size:0.82rem;color:{PALETTE['muted']};font-family:IBM Plex Sans,sans-serif'>"
    f"Central bank assets in trillions {currency} · {eq_label} index level · "
    f"{date_start.strftime('%b %d, %Y')} – {date_end.strftime('%b %d, %Y')}"
    f"</span>",
    unsafe_allow_html=True,
)

if view_mode == "Rebased":
    try:
        df_plot = rebase_to_100(df, baseline_year)
        fig_main = build_rebased_chart(df_plot, cb_label, eq_label, segments, plotly_template)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()
else:
    fig_main = build_dual_axis_chart(
        df, cb_label, eq_label, segments, plotly_template, cb_axis_title, eq_axis_title
    )

st.plotly_chart(fig_main, width="stretch")

_text = PALETTE["text"]
st.markdown(
    f"<div style='font-family:Fraunces,serif;font-size:1.1rem;color:{_text};margin-top:1rem'>"
    "Rolling Correlation</div>",
    unsafe_allow_html=True,
)
render_metric_grid(corr_result)
fig_corr = build_correlation_chart(corr_result, plotly_template)
st.plotly_chart(fig_corr, width="stretch")
