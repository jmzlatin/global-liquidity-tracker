# TASKS_UI.md — UI Elevation Pass

Portfolio-grade UI overhaul for the Global Liquidity Tracker. The app works and the
palette is in place; this pass makes it read as a designed financial terminal instead
of a themed Streamlit default.

Each task is self-contained: files, exact build steps, acceptance check. Execute in
order within a group; groups A→G are ordered by impact. Honor the layer rules from
CLAUDE.md throughout: UI never touches the network, `app.py` stays thin, anything
computed from data lives in `src/processing/`.

Palette reference (from `config/settings.py` `PALETTE`):

| Key | Hex | rgba base |
|---|---|---|
| background | `#F4F1E9` | `rgba(244,241,233,α)` |
| panel | `#E9E3D6` | `rgba(233,227,214,α)` |
| text | `#20232A` | `rgba(32,35,42,α)` |
| brass | `#C68A2E` | `rgba(198,138,46,α)` |
| verdigris | `#2E8B83` | `rgba(46,139,131,α)` |
| expansion | `#BFD8B8` | `rgba(191,216,184,α)` |
| contraction | `#E3B4A4` | `rgba(227,180,164,α)` |
| muted | `#9A968C` | `rgba(154,150,140,α)` |

After every task: `ruff check . && ruff format .` and a visual check with
`streamlit run app.py`.

---

## Group A — Kill the Streamlit chrome, own the page

**A1. Hide default Streamlit chrome**
- Files: `src/ui/theme.py`
- Append to `_CSS_TEMPLATE`:
  - `header[data-testid="stHeader"] { background: transparent; }` and hide its
    contents: `.stAppDeployButton, #MainMenu { display: none; }`
  - Keep the sidebar collapse control visible — do NOT hide
    `[data-testid="stSidebarCollapseButton"]`.
  - Tighten the dead space the header leaves behind:
    `.block-container { padding-top: 2.5rem; max-width: 1180px; }`
    (the max-width centers content and fixes the stranded right margin on wide
    screens).
- Accept: no "Deploy" button or hamburger menu anywhere; content column is centered
  with even margins at 1600px wide; sidebar can still collapse/expand.

**A2. Hero header block**
- Files: `src/ui/components.py` (new `render_hero()`), `app.py`, `src/ui/theme.py`
- Replace the current `st.markdown(f"## {region} — …")` + caption in `app.py` with
  one `render_hero(region, cb_label, eq_label, currency, date_start, date_end)` call
  that emits a single HTML block (one `st.markdown(..., unsafe_allow_html=True)`):
  - Eyebrow line: `LIQUIDITY · {region.upper()}` — IBM Plex Mono, 0.72rem,
    letter-spacing 0.14em, color muted.
  - Title: `{cb_label} vs {eq_label}` — Fraunces, ~2.1rem, weight 600, color text.
  - Sub line: the existing unit/date-range caption text, IBM Plex Sans 0.85rem muted.
  - Bottom border: `border-bottom: 1px solid rgba(154,150,140,0.4); padding-bottom: 1rem; margin-bottom: 1.25rem;`
- Move all styling into CSS classes in `theme.py` (`.hero-eyebrow`, `.hero-title`,
  `.hero-sub`) rather than inline styles.
- Accept: page leads with eyebrow/title/sub in three distinct type styles; the old
  `##` markdown title is gone from `app.py`.

**A3. Relocate and restyle the "What is this?" explainer**
- Files: `app.py`, `src/ui/theme.py`
- Move the `st.expander("What is this?")` block from the top of the page to directly
  below the correlation chart (it's reference material, not the headline).
- Restyle expanders in CSS:
  `[data-testid="stExpander"] details { background: #E9E3D6; border: 1px solid rgba(154,150,140,0.5); border-radius: 8px; }`
  and set the summary text to Fraunces.
- Accept: first visible row of the app is the hero, not an expander; the expander
  shows panel background with a hairline border and serif summary text.

**A4. Themed loading state**
- Files: `app.py`, `src/ui/theme.py`
- Replace `st.spinner("Loading data…")` text with `"Fetching central bank data…"`.
- Style the spinner in CSS: `[data-testid="stSpinner"] p { font-family: 'IBM Plex Mono', monospace; color: #9A968C; font-size: 0.8rem; }`
- Also restyle `st.warning`/`st.error` boxes to fit the palette:
  `[data-testid="stAlert"] { background: #E9E3D6; border: 1px solid #C68A2E; border-radius: 8px; color: #20232A; }`
- Accept: trigger a stale-cache warning (temporarily break the network or set
  manifest `fetched_at` old) — the warning renders in palette colors, not default
  Streamlit yellow.

---

## Group B — KPI strip (the "terminal" moment)

**B1. Summary stats module**
- Files: new `src/processing/summary.py`, new `tests/test_summary.py`
- Pure-pandas module (no Streamlit imports). Add a frozen dataclass `KpiSummary`:
  `cb_latest: float`, `cb_change_90d_pct: float`, `eq_latest: float`,
  `eq_change_90d_pct: float`, `regime_label: str` ("expansion"/"contraction"),
  `regime_since: pd.Timestamp`, `corr_90d: float`.
- `compute_summary(df: pd.DataFrame, segments: list[RegimeSegment], corr: CorrelationResult) -> KpiSummary`:
  latest = last row of `df`; 90d change = pct change vs the value 90 calendar days
  earlier via `df.asof`/index lookup with fallback to first row; regime fields from
  `segments[-1]`; `corr_90d` from `corr.latest[90]` (NaN-safe).
- Tests: synthetic 200-day frame with known values; assert each field, including the
  NaN path when the frame is shorter than 90 days.
- Accept: `pytest tests/test_summary.py -v` passes; module imports cleanly with no
  Streamlit dependency.

**B2. KPI cards row**
- Files: `src/ui/components.py` (new `render_kpi_row(summary, currency, eq_label)`),
  `src/ui/theme.py`, `app.py`
- Render four cards in `st.columns(4)` directly under the hero, each one HTML block
  using shared CSS classes:
  - `.kpi-card { background: #E9E3D6; border: 1px solid rgba(154,150,140,0.5); border-radius: 10px; padding: 0.9rem 1.1rem; }`
  - `.kpi-label` — mono 0.68rem uppercase letter-spacing 0.1em muted.
  - `.kpi-value` — IBM Plex Mono 1.45rem, color text.
  - `.kpi-delta` — mono 0.78rem; brass with `▲` when positive, verdigris with `▼`
    when negative (matches the line colors: brass=CB, verdigris=equity is fine, but
    for deltas use sign: positive `#2E8B83`-ish green is wrong here — use
    `#4A7C59` for positive and `#A14E3F` for negative so deltas aren't confused
    with the series colors).
- Cards: (1) Balance sheet — `{cb_latest:,.2f}T {currency}` + 90d delta;
  (2) `{eq_label}` — `{eq_latest:,.0f}` + 90d delta; (3) Regime — see B3;
  (4) 90-day correlation — `{corr_90d:+.3f}` colored by sign, "N/A" muted when NaN.
- `app.py` only computes `summary = compute_summary(...)` and calls the renderer.
- Accept: four equal-height cards under the hero; values match the chart's last
  points; switching region updates all four.

**B3. Regime status badge**
- Files: `src/ui/components.py`, `src/ui/theme.py`
- Card 3's value is a pill: `.regime-pill { display: inline-block; padding: 0.2rem 0.7rem; border-radius: 999px; font-family: 'IBM Plex Mono'; font-size: 0.85rem; letter-spacing: 0.06em; }`
  - expansion: `background: rgba(191,216,184,0.5); color: #2F5233; border: 1px solid #BFD8B8;` text `EXPANSION`
  - contraction: `background: rgba(227,180,164,0.5); color: #7A3B2E; border: 1px solid #E3B4A4;` text `CONTRACTION`
- Below the pill: `since {regime_since:%b %Y}` in `.kpi-delta` muted style.
- Accept: US full history today shows a pill whose label matches the sign of the
  last regime segment, with the correct start month.

---

## Group C — Main chart: from plot to centerpiece

**C1. Remove the modebar, everywhere**
- Files: `app.py`
- Pass `config={"displayModeBar": False}` to every `st.plotly_chart` call.
- Accept: hovering over either chart shows no Plotly toolbar.

**C2. Soft area fills under both lines**
- Files: `src/ui/charts.py`
- In `build_dual_axis_chart` and `build_rebased_chart`, give each Scatter trace a
  fill: CB trace `fill="tozeroy", fillcolor="rgba(198,138,46,0.07)"`; equity trace
  `fill="tozeroy", fillcolor="rgba(46,139,131,0.07)"`.
- Dual-axis gotcha: `tozeroy` on the secondary axis fills to that axis's zero —
  set `rangemode="tozero"` on both y-axes so fills don't extend below the data, OR
  keep autorange and accept the fill to zero (preferred: `rangemode="tozero"` on the
  equity axis only; the CB axis already starts near zero).
- Accept: both views show a faint tint under each line; lines and regime shading
  remain clearly readable; no fill bleeding above lines or below the x-axis.

**C3. Last-point markers and end labels**
- Files: `src/ui/charts.py`
- New helper `_add_endpoint(fig, x, y, text, color, secondary_y)` that adds (a) a
  4px marker Scatter at the last point (`showlegend=False`, `hoverinfo="skip"`) and
  (b) an annotation: `xanchor="left"`, `xshift=8`, text in IBM Plex Mono 11px in the
  trace color, e.g. `6.73T` / `6,038`. Call it for both traces in both chart
  builders. Format CB as `f"{y:,.2f}T"`, equity as `f"{y:,.0f}"`, rebased as
  `f"{y:,.0f}"`.
- Add `margin=dict(r=72)` (overriding template) so labels don't clip.
- Accept: each line ends in a dot with its current value floating just right of it,
  in the line's color, not clipped at the chart edge.

**C4. Themed unified hover + spike line**
- Files: `src/ui/theme.py` (template), `src/ui/charts.py`
- In the Plotly template layout add:
  `hoverlabel=dict(bgcolor="#E9E3D6", bordercolor="#9A968C", font=dict(family="IBM Plex Mono, monospace", size=12, color="#20232A"))`
  and on xaxis: `showspikes=True, spikemode="across", spikethickness=1, spikedash="dot", spikecolor="#9A968C"`.
- Date format in all hovertemplates: `%{x|%b %d, %Y}` (replace the ISO format).
- Accept: hover shows a panel-colored card with mono digits and a dotted vertical
  spike across the full plot height.

**C5. Quieter axes and grid**
- Files: `src/ui/theme.py`
- In `get_plotly_template` change `gridcolor` to `rgba(154,150,140,0.28)`, drop
  `linecolor`/`tickcolor` to `rgba(154,150,140,0.5)`, and set
  `xaxis.showgrid=False` (vertical gridlines add noise under regime shading; keep
  horizontal only). Remove the per-call `gridcolor`/`tickfont` overrides in
  `charts.py` `update_yaxes` that duplicate the template (keep `showgrid=False` on
  the secondary axis).
- Accept: gridlines are whisper-faint horizontal lines only; secondary axis still
  has no grid; nothing in `charts.py` re-specifies colors the template owns.

**C6. Make regime shading legible + add a key**
- Files: `config/settings.py`, `src/ui/charts.py`, `src/ui/components.py`, `app.py`
- Bump `EXPANSION_OPACITY` and `CONTRACTION_OPACITY` from 0.18 to 0.28 (the fills
  are nearly invisible on the paper background at 0.18).
- New `render_regime_key()` in `components.py`: one right-aligned HTML line directly
  under the main chart — `■ Expansion   ■ Contraction` with 10px squares in
  `#BFD8B8` / `#E3B4A4` (CSS class `.regime-key`, mono 0.7rem muted text). Call it
  from `app.py` after the main chart.
- Accept: shading is visible at a glance in the dual-axis view; the key sits under
  the chart, right-aligned, and explains the two band colors.

**C7. Range selector buttons on the main chart**
- Files: `src/ui/charts.py`
- Add to both main chart builders:
  ```python
  xaxis=dict(rangeselector=dict(
      buttons=[
          dict(count=1, label="1Y", step="year", stepmode="backward"),
          dict(count=5, label="5Y", step="year", stepmode="backward"),
          dict(count=10, label="10Y", step="year", stepmode="backward"),
          dict(step="all", label="MAX"),
      ],
      bgcolor="#E9E3D6", activecolor="#C68A2E",
      bordercolor="rgba(154,150,140,0.5)", borderwidth=1,
      font=dict(family="IBM Plex Mono, monospace", size=11, color="#20232A"),
      x=1.0, xanchor="right", y=1.08, yanchor="bottom",
  ))
  ```
- Keep the legend at top-left (y=1.02) — verify the two don't collide; if they do,
  raise the rangeselector to y=1.12.
- Accept: 1Y/5Y/10Y/MAX buttons render top-right of the chart in palette colors;
  clicking 1Y zooms client-side without a Streamlit rerun; active button is brass.

**C8. Crisis event markers on the full-history view**
- Files: `src/ui/charts.py`, `app.py`
- New helper `_add_crisis_markers(fig, crisis_windows, x_min, x_max)`: for each
  crisis window whose start falls inside the plotted range, `fig.add_vline` at the
  start date — `line_width=1, line_dash="dot", line_color="rgba(32,35,42,0.35)"` —
  plus `add_annotation` at the top: short label (`"2008"`, `"2020"`, `"2023"`),
  mono 10px muted, `textangle=0, yref="paper", y=1.0, yanchor="bottom"`.
- Pass `CRISIS_WINDOWS` (minus "Full History") through from `app.py`. Only draw a
  marker when the plotted span exceeds 3 years (skip when zoomed into one crisis).
- Accept: full-history view shows three faint dotted verticals labeled 2008/2020/
  2023; selecting the 2020 crisis window shows none.

---

## Group D — Controls that look designed

**D1. Crisis buttons → segmented control with active state**
- Files: `src/ui/components.py`, `src/ui/theme.py`, `app.py`
- Track the active window: `st.session_state["active_window"]` (default
  `"Full History"`). In `render_crisis_buttons`, render the active button with
  `type="primary"` and the rest `type="secondary"`; on click set
  `st.session_state["active_window"] = label` before returning the range.
- CSS: style primary buttons as the active segment —
  `.stButton > button[kind="primary"] { background: #C68A2E; border-color: #C68A2E; color: #F4F1E9; font-weight: 600; }`
  Secondary stays panel-colored. Remove all border-radius between them? No — keep
  them as four separate pills but with `border-radius: 999px; font-size: 0.78rem; font-family: 'IBM Plex Mono', monospace; letter-spacing: 0.03em;`.
- Add a mono uppercase micro-label above the row: `TIME WINDOW` (same style as
  `.kpi-label`).
- Accept: exactly one pill is brass-filled at any time and it matches the date range
  on the chart; clicking another pill moves the brass fill and reranges the chart.

**D2. Custom date range row**
- Files: `src/ui/components.py`, `app.py`
- Next to the crisis pills (5th column, slightly wider), add a `st.popover("Custom…")`
  containing two `st.date_input`s (From / To) seeded from session state and an
  "Apply" button that writes `date_start`/`date_end` to session state and sets
  `active_window = "Custom"` (no pill highlighted).
- Validate From < To; show `st.caption` error inside the popover otherwise and don't
  apply.
- Accept: picking Jan 2015 – Jan 2018 reranges chart, KPIs, and correlations; crisis
  pills all show inactive; reopening the popover shows the applied dates.

**D3. Sidebar redesign**
- Files: `src/ui/components.py`, `src/ui/theme.py`
- Brand block: a small glyph + wordmark —
  `<div class="brand"><span class="brand-glyph">◆</span> GLOBAL LIQUIDITY TRACKER</div>`
  glyph in brass, wordmark Fraunces 1.05rem letter-spacing 0.04em; replaces the
  current `## Global Liquidity Tracker`.
- Replace `st.markdown("---")` dividers with a CSS hairline
  (`.sidebar-rule { border-top: 1px solid rgba(154,150,140,0.4); margin: 1rem 0; }`)
  — the default `hr` is too heavy.
- View toggle: `st.radio(..., horizontal=True)` and CSS the radio into a segmented
  look: hide the circle (`[data-testid="stSidebar"] [role="radiogroup"] label > div:first-child { display: none; }`),
  give each label a pill border, brass-fill the checked one via
  `label:has(input:checked)`.
- Data freshness block (bottom, above the credit): new
  `render_freshness(manifest: dict)` showing per-series `fetched_at` as
  `WALCL · 3h ago` lines, mono 0.68rem muted. Read the manifest in `app.py` via the
  existing cache layer (add a pure `read_manifest()` accessor to
  `src/ingestion/cache.py` if one doesn't exist — UI must not touch the filesystem).
- Keep the "Developed by Jordan M. Zlatin" credit; add a GitHub link line under it:
  `<a href="https://github.com/...">View source ↗</a>` styled muted→brass on hover.
- Accept: sidebar reads brand → region → view toggle → freshness → credit, with
  hairline rules; radio looks like a two-segment switch; freshness ages update after
  a forced refetch.

---

## Group E — Correlation panel as a designed section

**E1. Section header + panel framing**
- Files: `app.py`, `src/ui/components.py`, `src/ui/theme.py`
- New `render_section_header(title, subtitle)` used for "Rolling Correlation":
  Fraunces 1.2rem title, muted 0.8rem subtitle ("How tightly liquidity and equities
  have moved together"), thin top rule above it (`margin-top: 2rem`). Replaces the
  inline-styled div in `app.py`.
- Accept: correlation section opens with a ruled, two-line header consistent with
  the hero typography.

**E2. Correlation metric cards with sign bars**
- Files: `src/ui/components.py`, `src/ui/theme.py`
- Upgrade `render_metric_grid` to card style (reuse `.kpi-card`). Under each value,
  a horizontal sign bar: a 4px track (`background: rgba(154,150,140,0.25); border-radius: 2px; position: relative;`)
  with a filled span from the 50% midpoint — width `abs(value) * 50%`, anchored
  `left: 50%` for positive (brass fill) and `right: 50%` for negative (verdigris
  fill). A 1px center tick at 50%. NaN → empty track.
- Keep the existing `corr-positive`/`corr-negative` value colors.
- Accept: a value of +0.50 fills the right quarter→half of the track in brass from
  center; −0.50 mirrors left in verdigris; N/A shows an empty track.

**E3. De-noise the correlation chart**
- Files: `src/ui/charts.py`
- The 30-day trace dominates as noise. Changes: 30-day line
  `opacity=0.35, width=1`; 90-day `width=1.8` (the visual lead); 1-year
  `width=1.8, dash="dot"`. Add shaded guide bands: `add_hrect` from 0.5→1.0 and
  −1.0→−0.5, `fillcolor="rgba(154,150,140,0.07)", line_width=0, layer="below"`.
  Raise chart `height` to 240. Same endpoint-label treatment as C3 for the 90-day
  trace only.
- Accept: the 90-day line reads as the primary series; bands mark the |r|>0.5 zones;
  the 30-day noise sits in the background.

---

## Group F — Storytelling and trust signals

**F1. Auto-generated insight line**
- Files: `src/processing/summary.py` (+ tests), `src/ui/components.py`, `app.py`
- `build_insight(summary: KpiSummary, region: str, eq_label: str) -> str`, pure
  string logic:
  `"The {bank short name} balance sheet has been in {regime} since {Mon YYYY}
  ({±x.x}% over 90 days), while the {eq_label} moved {±x.x}% over the same stretch."`
  Bank short name from region: US→"Fed", Eurozone→"ECB", Japan→"BOJ" (put the map in
  `config/settings.py`). Handle NaN deltas by omitting the parenthetical.
- Render via `render_insight(text)` between the KPI row and the main chart: a
  left-bordered callout — `border-left: 3px solid #C68A2E; padding: 0.4rem 1rem; font-family: Fraunces, serif; font-style: italic; font-size: 1.02rem; color: #20232A;`
- Tests: expansion and contraction phrasings, NaN handling.
- Accept: the sentence matches the KPI numbers exactly and updates with region and
  date range; reads naturally in both regime cases.

**F2. Footer with sources and disclaimer**
- Files: `src/ui/components.py`, `app.py`
- `render_footer(region)` at the very bottom: hairline top rule, then one muted
  0.72rem mono line —
  `Data: FRED ({series_id}) · Yahoo Finance ({ticker}) · Cached 24h · Not investment advice`
  with `FRED`/`Yahoo Finance` as links (`https://fred.stlouisfed.org/series/{id}`,
  `https://finance.yahoo.com/quote/{ticker}`), muted color, brass on hover.
  Centered, `padding: 2rem 0 1rem`.
- Accept: footer renders the correct series ID and ticker per region and both links
  resolve.

**F3. README hero screenshot refresh**
- Files: `README.md`, new `docs/screenshot-main.png`, `docs/screenshot-rebased.png`
- After Groups A–F land: run the app, capture full-page screenshots of the US
  dual-axis view and the rebased view at 1600×1300 (Playwright with
  `channel="chrome"` works; see `/tmp/shoot_glt.py` pattern from this session), save
  under `docs/`, and embed the main one at the top of the README with a one-line
  caption. Delete any stale screenshots.
- Accept: README's first screen shows the new UI; image files are < 600KB each
  (downscale if needed).

---

## Group G — Motion, dark mode, final polish

**G1. Micro-interactions**
- Files: `src/ui/theme.py`
- Add to the CSS:
  - Card hover: `.kpi-card { transition: transform .15s ease, box-shadow .15s ease; } .kpi-card:hover { transform: translateY(-2px); box-shadow: 0 4px 14px rgba(32,35,42,0.08); }`
  - Page entrance: `@keyframes fadeUp { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } } .block-container { animation: fadeUp .35s ease-out; }`
  - Brass text selection: `::selection { background: rgba(198,138,46,0.35); }`
  - Slim themed scrollbar: `::-webkit-scrollbar { width: 10px; } ::-webkit-scrollbar-thumb { background: rgba(154,150,140,0.5); border-radius: 5px; }`
- Accept: cards lift on hover, the page fades up once on load (no re-animation on
  every widget interaction — if Streamlit reruns retrigger it annoyingly, scope the
  animation to `.hero-*` elements only), selection highlight is brass.

**G2. Dark "terminal" variant**
- Files: `config/settings.py`, `src/ui/theme.py`, `src/ui/components.py`, `app.py`
- Add `PALETTE_DARK` to settings:
  `background #16181D, panel #1E2128, text #E8E4DA, brass #D99A3D, verdigris #43A89A, expansion #2E4A33, contraction #4A2F2A, muted #6E7178` (expansion/contraction opacity 0.35 in dark).
- Refactor `theme.py`: `inject_css(palette: dict)` and
  `get_plotly_template(palette: dict)` take the palette as an argument instead of
  importing `PALETTE` at module top. Every component that hardcodes a hex from this
  document must read from the active palette instead — sweep `components.py` and
  `charts.py` for literals.
- Toggle: `st.sidebar` segmented control (reuse D3's radio styling) "Paper / Terminal"
  stored in `st.session_state["theme"]`; `app.py` picks the palette dict and passes
  it down. Known limitation: `.streamlit/config.toml` is static, so native widget
  internals (selectbox dropdown list) may stay light — override what CSS can reach
  (`[data-testid="stSidebar"]`, inputs, buttons, `body`/`.stApp` background) and
  accept the rest; note the limitation in README.
- Accept: flipping the toggle restyles background, panels, text, both charts
  (including regime shading and hover cards) without restart; no unreadable
  light-on-light or dark-on-dark text in either mode.

**G3. Responsive + cross-region sweep**
- Files: whatever the sweep flags
- Check at 1280px and ~900px widths (browser devtools): KPI row (4 cards) may need
  `flex-wrap` to 2×2 — if Streamlit columns squeeze, render the KPI row as one HTML
  flex container instead of `st.columns` (`display: flex; flex-wrap: wrap; gap: 0.8rem;`
  with `flex: 1 1 220px` per card). Verify all three regions × both views × every
  crisis window: endpoint labels not clipped, JPY trillions formatted sanely
  (BOJ ≈ 700T JPY — confirm the KPI card doesn't overflow), no console errors.
- Accept: no overlapping or clipped UI at 1280px; all 24 region/view/window combos
  render without errors or layout breaks.

**G4. Lighthouse-style final pass**
- Files: `app.py`, `src/ui/theme.py`
- Set `page_icon` to a brass-toned emoji or inline SVG data-URI diamond (◆) instead
  of 📊; confirm `page_title="Global Liquidity Tracker"`. Add
  `<meta name="description">`? Not injectable in Streamlit — skip. Run
  `ruff check . && pytest` and fix anything the UI pass broke. Re-read every CSS
  selector against the running app once (Streamlit version bumps rename
  `data-testid`s — verify each selector actually matches in devtools).
- Accept: browser tab shows the custom icon and title; `pytest` and `ruff` clean;
  zero dead CSS selectors.

---

## Suggested order & scoping notes

- A → B → C are the visible 80%: chrome removal, hero, KPI cards, chart finish.
- D and E make the controls and correlation panel match. F adds the storytelling
  layer that interviews well ("the app writes its own market commentary").
- G2 (dark terminal) is the single biggest "wow" for a portfolio — but do it last;
  it touches every file and is much cheaper once all colors flow from one palette
  dict.
- Never put computation in `components.py`/`charts.py` — anything derived from data
  goes through `src/processing/summary.py` with a test.
