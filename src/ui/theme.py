"""CSS injection and Plotly template for the paper-and-brass theme."""

import plotly.graph_objects as go
import streamlit as st


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


_GOOGLE_FONTS_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=Fraunces:ital,wght@0,400;0,600;0,700;1,400;1,600&"
    "family=IBM+Plex+Sans:wght@400;500;600&"
    "family=IBM+Plex+Mono:wght@400;500;600&"
    "display=swap"
)

_CSS_TEMPLATE = """
<link href="{fonts_url}" rel="stylesheet">
<style>
  /* ── Motion vocabulary ──────────────────────────────────── */
  @keyframes fadeUp {{
    from {{ opacity: 0; transform: translateY(10px); }}
    to {{ opacity: 1; transform: none; }}
  }}
  @keyframes fadeIn {{
    from {{ opacity: 0; }}
    to {{ opacity: 1; }}
  }}
  @keyframes drawRule {{
    from {{ width: 0; opacity: 0; }}
    to {{ width: 64px; opacity: 1; }}
  }}
  @keyframes drawLine {{
    to {{ stroke-dashoffset: 0; }}
  }}
  @keyframes growBar {{
    from {{ transform: scaleX(0); }}
    to {{ transform: scaleX(1); }}
  }}
  @keyframes pulse {{
    0% {{ box-shadow: 0 0 0 0 {brass_glow}; }}
    70% {{ box-shadow: 0 0 0 7px rgba(0,0,0,0); }}
    100% {{ box-shadow: 0 0 0 0 rgba(0,0,0,0); }}
  }}
  @keyframes breathe {{
    0%, 100% {{ opacity: 0.55; transform: scale(0.96); }}
    50% {{ opacity: 1; transform: scale(1.04); }}
  }}
  @keyframes accentDrift {{
    0% {{ background-position: 0% 50%; }}
    100% {{ background-position: 200% 50%; }}
  }}
  @keyframes sheen {{
    from {{ transform: translateX(-150%) skewX(-18deg); }}
    to {{ transform: translateX(320%) skewX(-18deg); }}
  }}

  /* ── App chrome ─────────────────────────────────────────── */
  html {{
    scroll-behavior: smooth;
  }}
  body {{
    background-color: {background};
  }}
  .stApp {{
    background:
      radial-gradient(1100px 600px at 12% -8%, {brass_wash}, transparent 60%),
      radial-gradient(900px 600px at 95% 0%, {verdigris_wash}, transparent 60%),
      {background};
    background-attachment: fixed;
  }}
  .stApp::before {{
    content: "";
    position: fixed;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, {brass}, {verdigris}, {brass});
    background-size: 200% 100%;
    animation: accentDrift 14s linear infinite;
    z-index: 999999;
    pointer-events: none;
  }}
  header[data-testid="stHeader"] {{
    background: transparent;
  }}
  .stAppDeployButton, #MainMenu {{
    display: none;
  }}
  .block-container {{
    padding-top: 2.5rem;
    max-width: 1180px;
  }}

  /* ── Sidebar ─────────────────────────────────────────────── */
  section[data-testid="stSidebar"] {{
    background-color: {panel};
    border-right: 1px solid {hairline};
  }}
  .sidebar-rule {{
    border-top: 1px solid {hairline};
    margin: 1rem 0;
  }}
  .brand {{
    font-family: 'Fraunces', serif;
    font-size: 1.05rem;
    letter-spacing: 0.04em;
    color: {text};
    margin-bottom: 0.15rem;
  }}
  .brand-glyph {{
    color: {brass};
    display: inline-block;
    animation: breathe 3.5s ease-in-out infinite;
  }}
  .freshness-block {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.68rem;
    color: {muted};
    line-height: 1.9;
  }}

  /* ── Typography ──────────────────────────────────────────── */
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
  .kpi-value, .corr-positive, .corr-negative, .corr-neutral,
  .kpi-delta-pos, .kpi-delta-neg, .kpi-delta-neutral, .freshness-block {{
    font-variant-numeric: tabular-nums;
  }}

  /* ── Hero block ──────────────────────────────────────────── */
  .hero-block {{
    border-bottom: 1px solid {hairline};
    padding-bottom: 1.1rem;
    margin-bottom: 1.35rem;
  }}
  .hero-eyebrow {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem;
    letter-spacing: 0.14em;
    color: {muted};
    text-transform: uppercase;
    margin-bottom: 0.3rem;
    display: flex;
    align-items: center;
    gap: 0.55rem;
    animation: fadeUp 0.45s ease-out backwards;
  }}
  .pulse-dot {{
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: {brass};
    display: inline-block;
    flex: 0 0 auto;
    animation: pulse 2.4s ease-out infinite;
  }}
  .hero-title {{
    font-family: 'Fraunces', serif;
    font-size: 2.3rem;
    font-weight: 600;
    letter-spacing: -0.01em;
    color: {text};
    line-height: 1.2;
    margin-bottom: 0.35rem;
    animation: fadeUp 0.5s ease-out 0.06s backwards;
  }}
  .hero-title .hero-vs {{
    font-style: italic;
    font-weight: 400;
    font-size: 1.55rem;
    color: {brass};
    padding: 0 0.15rem;
  }}
  .hero-title::after {{
    content: "";
    display: block;
    height: 3px;
    width: 64px;
    border-radius: 2px;
    background: linear-gradient(90deg, {brass}, {verdigris});
    margin-top: 0.55rem;
    animation: drawRule 0.9s ease-out 0.3s backwards;
  }}
  .hero-sub {{
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 0.85rem;
    color: {muted};
    margin-bottom: 0;
    animation: fadeUp 0.5s ease-out 0.14s backwards;
  }}

  /* ── KPI cards ───────────────────────────────────────────── */
  .kpi-card {{
    position: relative;
    overflow: hidden;
    background: {panel};
    border: 1px solid {hairline_strong};
    border-radius: 12px;
    padding: 1rem 1.15rem;
    min-height: 118px;
    height: 100%;
    box-shadow: 0 1px 2px rgba(20,18,12,0.04), 0 4px 16px rgba(20,18,12,0.05);
    transition:
      transform 0.22s cubic-bezier(0.2, 0.8, 0.3, 1),
      box-shadow 0.22s ease,
      border-color 0.22s ease;
    animation: fadeUp 0.5s ease-out backwards;
  }}
  .kpi-card:hover {{
    transform: translateY(-3px);
    border-color: {brass};
    box-shadow:
      0 2px 4px rgba(20,18,12,0.05),
      0 12px 28px rgba(20,18,12,0.10),
      0 0 0 1px {brass_glow};
  }}
  .kpi-card::before {{
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
  }}
  .accent-brass::before {{
    background: linear-gradient(90deg, {brass}, transparent 70%);
  }}
  .accent-verdigris::before {{
    background: linear-gradient(90deg, {verdigris}, transparent 70%);
  }}
  .accent-expansion::before {{
    background: linear-gradient(90deg, {expansion}, transparent 70%);
  }}
  .accent-contraction::before {{
    background: linear-gradient(90deg, {contraction}, transparent 70%);
  }}
  .accent-muted::before {{
    background: linear-gradient(90deg, {muted}, transparent 70%);
  }}
  .kpi-card::after {{
    content: "";
    position: absolute;
    top: 0; bottom: 0; left: 0;
    width: 45%;
    background: linear-gradient(105deg, transparent, rgba(255,255,255,0.16), transparent);
    transform: translateX(-150%) skewX(-18deg);
    pointer-events: none;
  }}
  .kpi-card:hover::after {{
    animation: sheen 0.9s ease;
  }}
  .stagger-1 {{ animation-delay: 0.04s; }}
  .stagger-2 {{ animation-delay: 0.10s; }}
  .stagger-3 {{ animation-delay: 0.16s; }}
  .stagger-4 {{ animation-delay: 0.22s; }}
  .kpi-flex {{
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    gap: 0.6rem;
  }}
  .kpi-spark {{
    flex: 0 0 auto;
    line-height: 0;
    opacity: 0.95;
  }}
  .spark-line {{
    stroke-dasharray: 600;
    stroke-dashoffset: 600;
    animation: drawLine 1.3s ease-out 0.35s forwards;
  }}
  .spark-fill {{
    animation: fadeIn 0.9s ease-out 0.8s backwards;
  }}
  .spark-dot {{
    animation: fadeIn 0.4s ease-out 1.35s backwards;
  }}
  .kpi-label {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: {muted};
    margin-bottom: 0.25rem;
  }}
  .kpi-value {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.45rem;
    color: {text};
    margin-bottom: 0.2rem;
    white-space: nowrap;
  }}
  .kpi-unit {{
    font-size: 0.85rem;
    color: {muted};
  }}
  .kpi-delta-pos, .kpi-delta-neg, .kpi-delta-neutral {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.74rem;
    display: inline-block;
    padding: 0.08rem 0.45rem;
    border-radius: 6px;
    white-space: nowrap;
  }}
  .kpi-delta-pos {{
    color: {delta_pos};
    background: {delta_pos_soft};
  }}
  .kpi-delta-neg {{
    color: {delta_neg};
    background: {delta_neg_soft};
  }}
  .kpi-delta-neutral {{
    color: {muted};
    padding-left: 0;
  }}

  /* ── Regime pill ─────────────────────────────────────────── */
  .regime-pill {{
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.2rem 0.7rem;
    border-radius: 999px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.85rem;
    letter-spacing: 0.06em;
  }}
  .pill-dot {{
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: currentColor;
    animation: breathe 2.2s ease-in-out infinite;
  }}
  .regime-pill-expansion {{
    background: {expansion_soft};
    color: {expansion_ink};
    border: 1px solid {expansion};
  }}
  .regime-pill-contraction {{
    background: {contraction_soft};
    color: {contraction_ink};
    border: 1px solid {contraction};
  }}

  /* ── Regime key ──────────────────────────────────────────── */
  .regime-key {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem;
    color: {muted};
    text-align: right;
    margin-top: 0.3rem;
  }}

  /* ── Insight callout ─────────────────────────────────────── */
  .insight-callout {{
    border-left: 3px solid {brass};
    background: {brass_tint};
    border-radius: 0 12px 12px 0;
    padding: 0.7rem 1.1rem;
    font-family: 'Fraunces', serif;
    font-style: italic;
    font-size: 1.02rem;
    color: {text};
    margin-bottom: 1rem;
    animation: fadeIn 0.7s ease-out 0.25s backwards;
  }}

  /* ── Chart frames ────────────────────────────────────────── */
  [data-testid="stPlotlyChart"] {{
    border: 1px solid {hairline};
    border-radius: 14px;
    overflow: hidden;
    background: {background};
    padding: 0.35rem 0.35rem 0;
    box-shadow: 0 1px 2px rgba(20,18,12,0.04), 0 10px 30px rgba(20,18,12,0.06);
    animation: fadeIn 0.6s ease-out backwards;
  }}

  /* ── Section header ──────────────────────────────────────── */
  .section-header {{
    border-top: 1px solid {hairline};
    margin-top: 2rem;
    padding-top: 1rem;
  }}
  .section-title {{
    font-family: 'Fraunces', serif;
    font-size: 1.2rem;
    color: {text};
    margin-bottom: 0.15rem;
  }}
  .section-subtitle {{
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 0.8rem;
    color: {muted};
    margin-bottom: 0;
  }}

  /* ── Correlation sign bars ───────────────────────────────── */
  .sign-bar-track {{
    position: relative;
    height: 4px;
    background: {muted_25};
    border-radius: 2px;
    margin-top: 0.4rem;
    overflow: hidden;
  }}
  .sign-bar-center {{
    position: absolute;
    left: 50%;
    top: 0;
    width: 1px;
    height: 4px;
    background: {hairline_strong};
  }}
  .sign-bar-fill-pos {{
    position: absolute;
    left: 50%;
    top: 0;
    height: 4px;
    background: {brass};
    border-radius: 0 2px 2px 0;
    transform-origin: left;
    animation: growBar 0.8s cubic-bezier(0.2, 0.8, 0.3, 1) 0.2s backwards;
  }}
  .sign-bar-fill-neg {{
    position: absolute;
    top: 0;
    right: 50%;
    height: 4px;
    background: {verdigris};
    border-radius: 2px 0 0 2px;
    transform-origin: right;
    animation: growBar 0.8s cubic-bezier(0.2, 0.8, 0.3, 1) 0.2s backwards;
  }}

  /* ── Correlation metric labels ───────────────────────────── */
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

  /* ── Buttons ─────────────────────────────────────────────── */
  .stButton > button,
  [data-testid="stPopover"] button {{
    background-color: {panel};
    border: 1px solid {hairline_strong};
    color: {text};
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.78rem;
    letter-spacing: 0.03em;
    border-radius: 999px;
    box-shadow: 0 1px 2px rgba(20,18,12,0.05);
    transition:
      transform 0.18s ease,
      box-shadow 0.18s ease,
      background-color 0.18s ease,
      border-color 0.18s ease,
      color 0.18s ease;
  }}
  .stButton > button:hover,
  [data-testid="stPopover"] button:hover {{
    background-color: {brass};
    border-color: {brass};
    color: {background};
    transform: translateY(-1px);
    box-shadow: 0 4px 12px {brass_glow};
  }}
  .stButton > button:active,
  [data-testid="stPopover"] button:active {{
    transform: translateY(0) scale(0.97);
  }}
  .stButton > button[kind="primary"] {{
    background: {brass};
    border-color: {brass};
    color: {background};
    font-weight: 600;
    box-shadow: 0 2px 10px {brass_glow};
  }}

  /* ── Time window label ───────────────────────────────────── */
  .time-window-label {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: {muted};
    margin-bottom: 0.3rem;
  }}

  /* ── Expanders ───────────────────────────────────────────── */
  [data-testid="stExpander"] details {{
    background: {panel};
    border: 1px solid {hairline_strong};
    border-radius: 8px;
    transition: border-color 0.2s ease;
  }}
  [data-testid="stExpander"] details:hover {{
    border-color: {brass};
  }}
  [data-testid="stExpander"] details summary {{
    font-family: 'Fraunces', serif;
  }}

  /* ── Spinner / alerts ────────────────────────────────────── */
  [data-testid="stSpinner"] p {{
    font-family: 'IBM Plex Mono', monospace;
    color: {muted};
    font-size: 0.8rem;
  }}
  [data-testid="stAlert"] {{
    background: {panel};
    border: 1px solid {brass};
    border-radius: 8px;
    color: {text};
    animation: fadeUp 0.4s ease-out;
  }}

  /* ── Sidebar radio as segmented control ──────────────────── */
  [data-testid="stSidebar"] [role="radiogroup"] label > div:first-child {{
    display: none;
  }}
  [data-testid="stSidebar"] [role="radiogroup"] label {{
    border: 1px solid {hairline_strong};
    padding: 0.25rem 0.75rem;
    border-radius: 999px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.8rem;
    cursor: pointer;
    transition: background-color 0.18s ease, border-color 0.18s ease,
      color 0.18s ease;
  }}
  [data-testid="stSidebar"] [role="radiogroup"] label:hover {{
    border-color: {brass};
  }}
  [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {{
    background: {brass};
    border-color: {brass};
    color: {background};
  }}

  /* ── Widget backgrounds (auto-adapts to active palette) ──── */
  [data-baseweb="select"] > div,
  [data-baseweb="select"] > div > div {{
    background-color: {panel} !important;
    border-color: {hairline} !important;
    transition: border-color 0.18s ease, box-shadow 0.18s ease;
  }}
  [data-baseweb="select"] > div:focus-within {{
    border-color: {brass} !important;
    box-shadow: 0 0 0 3px {brass_tint} !important;
  }}
  [data-baseweb="select"] span {{
    color: {text} !important;
  }}
  [data-baseweb="input"] > div {{
    background-color: {panel} !important;
    border-color: {hairline} !important;
  }}
  [data-baseweb="input"] input {{
    color: {text} !important;
  }}
  [data-testid="stNumberInput"] input,
  [data-testid="stDateInput"] input {{
    background-color: {panel} !important;
    color: {text} !important;
  }}

  /* ── Footer ──────────────────────────────────────────────── */
  .footer {{
    border-top: 1px solid {hairline};
    text-align: center;
    padding: 2rem 0 1rem;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem;
    color: {muted};
  }}
  .footer a {{
    color: {muted};
    text-decoration: none;
    transition: color 0.15s;
  }}
  .footer a:hover {{
    color: {brass};
  }}

  /* ── Finish ──────────────────────────────────────────────── */
  ::selection {{
    background: {selection};
  }}
  ::-webkit-scrollbar {{
    width: 10px;
  }}
  ::-webkit-scrollbar-thumb {{
    background: {hairline_strong};
    border-radius: 5px;
  }}
  @media (prefers-reduced-motion: reduce) {{
    *, *::before, *::after {{
      animation-duration: 0.01ms !important;
      animation-iteration-count: 1 !important;
      transition-duration: 0.01ms !important;
    }}
  }}
</style>
"""


def _palette_vars(palette: dict) -> dict:
    """Extend the palette with derived rgba shades used by the CSS template."""
    return {
        **palette,
        "hairline": _hex_to_rgba(palette["muted"], 0.35),
        "hairline_strong": _hex_to_rgba(palette["muted"], 0.5),
        "muted_25": _hex_to_rgba(palette["muted"], 0.25),
        "brass_glow": _hex_to_rgba(palette["brass"], 0.35),
        "brass_tint": _hex_to_rgba(palette["brass"], 0.07),
        "brass_wash": _hex_to_rgba(palette["brass"], 0.05),
        "verdigris_wash": _hex_to_rgba(palette["verdigris"], 0.045),
        "expansion_soft": _hex_to_rgba(palette["expansion"], 0.45),
        "contraction_soft": _hex_to_rgba(palette["contraction"], 0.45),
        "delta_pos_soft": _hex_to_rgba(palette["delta_pos"], 0.13),
        "delta_neg_soft": _hex_to_rgba(palette["delta_neg"], 0.13),
        "selection": _hex_to_rgba(palette["brass"], 0.35),
    }


def inject_css(palette: dict) -> None:
    """Inject Google Fonts and custom CSS for the active palette theme."""
    css = _CSS_TEMPLATE.format(fonts_url=_GOOGLE_FONTS_URL, **_palette_vars(palette))
    # Streamlit's markdown parser ends a raw-HTML block at the first blank line,
    # which would truncate the <style> tag mid-sheet. Strip blank lines so the
    # whole block survives as one contiguous chunk of HTML.
    css = "\n".join(line for line in css.splitlines() if line.strip())
    # Wrap in a display:none container so Streamlit doesn't render the style/link
    # text as visible content — the browser still processes <link> and <style>
    # regardless of the parent element's visibility.
    st.markdown(
        f"<div style='display:none;height:0;overflow:hidden'>{css}</div>",
        unsafe_allow_html=True,
    )


def get_plotly_template(palette: dict) -> go.layout.Template:
    """Build and return a Plotly layout template matching the active palette."""
    muted_28 = _hex_to_rgba(palette["muted"], 0.28)
    muted_50 = _hex_to_rgba(palette["muted"], 0.5)
    axis_common = dict(
        gridcolor=muted_28,
        gridwidth=0.5,
        linecolor=muted_50,
        tickcolor=muted_50,
        tickfont=dict(
            family="IBM Plex Mono, monospace", color=palette["muted"], size=11
        ),
        title_font=dict(
            family="IBM Plex Sans, sans-serif", color=palette["text"], size=12
        ),
        zeroline=False,
    )
    xaxis_common = dict(
        **axis_common,
        showgrid=False,
        showspikes=True,
        spikemode="across",
        spikethickness=1,
        spikedash="dot",
        spikecolor=palette["muted"],
    )
    return go.layout.Template(
        layout=go.Layout(
            font=dict(family="IBM Plex Sans, sans-serif", color=palette["text"]),
            paper_bgcolor=palette["background"],
            plot_bgcolor=palette["panel"],
            colorway=[palette["brass"], palette["verdigris"]],
            xaxis=xaxis_common,
            yaxis=axis_common,
            hoverlabel=dict(
                bgcolor=palette["panel"],
                bordercolor=palette["muted"],
                font=dict(
                    family="IBM Plex Mono, monospace", size=12, color=palette["text"]
                ),
            ),
            legend=dict(
                bgcolor=palette["panel"],
                bordercolor=palette["muted"],
                borderwidth=1,
                font=dict(
                    family="IBM Plex Sans, sans-serif", color=palette["text"], size=12
                ),
            ),
            margin=dict(l=64, r=72, t=48, b=48),
        )
    )
