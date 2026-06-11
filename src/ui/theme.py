"""CSS injection and Plotly template for the paper-and-brass theme."""

import plotly.graph_objects as go
import streamlit as st

from config.settings import PALETTE

_GOOGLE_FONTS_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=Fraunces:ital,wght@0,400;0,600;1,400&"
    "family=IBM+Plex+Sans:wght@400;500&"
    "family=IBM+Plex+Mono:wght@400;500&"
    "display=swap"
)

_CSS_TEMPLATE = """
<link href="{fonts_url}" rel="stylesheet">
<style>
  .stApp {{
    background-color: {background};
  }}
  section[data-testid="stSidebar"] {{
    background-color: {panel};
    border-right: 1px solid {muted};
  }}
  h1, h2, h3 {{
    font-family: 'Fraunces', serif;
    color: {text};
  }}
  p, label, div.stMarkdown {{
    font-family: 'IBM Plex Sans', sans-serif;
    color: {text};
  }}
  [data-testid="stMetricValue"] {{
    font-family: 'IBM Plex Mono', monospace;
  }}
  .stButton > button {{
    background-color: {panel};
    border: 1px solid {muted};
    color: {text};
    font-family: 'IBM Plex Sans', sans-serif;
    border-radius: 4px;
    transition: background-color 0.15s;
  }}
  .stButton > button:hover {{
    background-color: {brass};
    border-color: {brass};
    color: {text};
  }}
  .corr-positive {{
    color: {brass};
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.35rem;
    font-weight: 500;
  }}
  .corr-negative {{
    color: {verdigris};
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.35rem;
    font-weight: 500;
  }}
  .corr-neutral {{
    color: {muted};
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.35rem;
    font-weight: 400;
  }}
  .corr-label {{
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 0.78rem;
    color: {muted};
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }}
</style>
"""


def inject_css() -> None:
    """Inject Google Fonts and custom CSS for the paper-and-brass theme."""
    css = _CSS_TEMPLATE.format(fonts_url=_GOOGLE_FONTS_URL, **PALETTE)
    st.markdown(css, unsafe_allow_html=True)


def get_plotly_template() -> go.layout.Template:
    """Build and return a Plotly layout template matching the paper-and-brass palette."""
    axis_common = dict(
        gridcolor=PALETTE["muted"],
        gridwidth=0.5,
        linecolor=PALETTE["muted"],
        tickcolor=PALETTE["muted"],
        tickfont=dict(family="IBM Plex Mono, monospace", color=PALETTE["muted"], size=11),
        title_font=dict(family="IBM Plex Sans, sans-serif", color=PALETTE["text"], size=12),
        zeroline=False,
    )
    return go.layout.Template(
        layout=go.Layout(
            font=dict(family="IBM Plex Sans, sans-serif", color=PALETTE["text"]),
            paper_bgcolor=PALETTE["background"],
            plot_bgcolor=PALETTE["panel"],
            colorway=[PALETTE["brass"], PALETTE["verdigris"]],
            xaxis=axis_common,
            yaxis=axis_common,
            legend=dict(
                bgcolor=PALETTE["panel"],
                bordercolor=PALETTE["muted"],
                borderwidth=1,
                font=dict(family="IBM Plex Sans, sans-serif", color=PALETTE["text"], size=12),
            ),
            margin=dict(l=64, r=48, t=48, b=48),
        )
    )
