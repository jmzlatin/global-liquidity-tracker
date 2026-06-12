# TASKS.md

Phased build roadmap for the Global Market Liquidity & Central Bank Tracker. Each task lists a goal, the files involved, an acceptance check, and a time estimate. Estimates assume an experienced Python dev working with Claude Code.

Total estimate: 17 to 26 hours across 7 phases.

---

## Phase 0: Project setup (~1 hour)

**0.1 Scaffold the repo**
- Create the folder structure from CLAUDE.md.
- Add `.gitignore` covering `.env`, `data/cache/`, `__pycache__`, `.streamlit/secrets.toml`.
- Create `requirements.txt` and `.env.example`.
- Accept: `pip install -r requirements.txt` succeeds in a clean venv.

**0.2 Config constants**
- Build `config/settings.py` with series IDs, tickers, crisis windows, baseline year default, and the palette dict.
- Accept: importing settings returns all constants with no missing keys.

---

## Phase 1: Data ingestion and cache (3 to 4 hours)

**1.1 FRED client**
- `src/ingestion/fred_client.py`. Function takes a series ID and returns a clean pandas Series indexed by date.
- Convert `"."` to NaN. Parse dates to timezone-naive.
- Read the key from env or `st.secrets`.
- Accept: a live call to `WALCL` returns a sorted Series with a DatetimeIndex.

**1.2 Equity client**
- `src/ingestion/equity_client.py`. Wrap `yf.download`, return a single Close Series.
- Flatten MultiIndex columns.
- Accept: `^GSPC` returns one Close Series, no MultiIndex.

**1.3 Cache layer**
- `src/ingestion/cache.py`. Read and write CSV per series plus `manifest.json` with `fetched_at`.
- 24h freshness check. Stale-fallback on fetch failure.
- Accept: first run hits the network, second run within 24h reads local files only. Simulate a fetch failure and confirm the stale file loads with a warning flag.

---

## Phase 2: Analytical and normalization engine (2 to 3 hours)

**2.1 Merge and forward-fill**
- `src/processing/normalize.py`. Build the union daily index, reindex both series, forward-fill.
- Accept: weekly central bank values carry forward to daily, no gaps after the first valid date.

**2.2 Rebase to 100**
- Add a rebase function keyed to a baseline year.
- Accept: both series equal 100 at the first observation of the baseline year and scale correctly after.

**2.3 Regime engine**
- `src/processing/regimes.py`. Rolling 90-day slope, sign classification, contiguous segment list with start, end, and label.
- Accept: returns a list of expansion and contraction segments covering the full range with no overlaps.

**2.4 Correlation engine**
- `src/processing/correlation.py`. `pct_change` on both, rolling corr for 30, 90, 360. Drop NaN. Return latest values plus the rolling correlation Series.
- Accept: latest values fall in the -1 to 1 range for a region with real overlap.

---

## Phase 3: UI skeleton and theme (2 to 3 hours)

**3.1 Streamlit config**
- Write `.streamlit/config.toml` with the paper theme.
- Accept: running the app shows the warm background, not Streamlit default white and red.

**3.2 Theme module**
- `src/ui/theme.py`. Inject Google Fonts and custom CSS for headings, body, mono metrics, panels, and buttons. Build and export one Plotly template.
- Accept: headings render in the serif face, metric values in mono, buttons use brass on hover.

**3.3 App shell and sidebar**
- `app.py` plus `src/ui/components.py`. Single sidebar dropdown with the three explicit region labels. Page title and layout.
- Accept: selecting a region triggers a data load and a placeholder chart.

---

## Phase 4: Core chart with regime shading (3 to 4 hours)

**4.1 Dual-axis chart**
- `src/ui/charts.py`. Brass central bank line on the primary axis, verdigris equity line on the secondary axis. Apply the Plotly template.
- Accept: both lines render with labeled dual axes and a shared hover.

**4.2 Regime shading**
- Draw each regime segment as a `vrect` behind the lines. Sage for expansion, clay for contraction, low opacity.
- Accept: shaded bands match the slope sign and sit behind the data lines.

**4.3 Rebase toggle**
- Add a control to switch between raw dual-axis and rebased single-axis at 100.
- Accept: toggling redraws without a full reload stall.

---

## Phase 5: Value-add features (2 to 3 hours)

**5.1 Correlation metric grid**
- `src/ui/components.py`. Grid of 30, 90, 360 day coefficients in mono type. Positive and negative colored differently. Small rolling correlation line chart below the main chart.
- Accept: the grid updates when the region changes.

**5.2 Crisis bookmark buttons**
- Quick buttons for 2008, 2020, 2023, and full history. A click sets the date range and reruns.
- Accept: clicking 2020 isolates the pandemic window on the chart and the metric grid recomputes for that span.

---

## Phase 6: UI design pass (2 to 3 hours)

This phase exists so the app reads as a designed product, not a default dashboard.

**6.1 Layout and spacing**
- Tune column widths, padding, and section dividers. Give the chart room to breathe. Group the metric grid and crisis buttons into a clean secondary panel.
- Accept: no cramped or overflowing sections at common screen widths.

**6.2 Polish the components**
- Style the metric cards with the panel background, hairline border, and rounded corners. Refine button states. Add a compact header strip with the region name and last-updated timestamp.
- Accept: cards, buttons, and header share one consistent visual language.

**6.3 Chart finish**
- Refine grid line color, axis label fonts, legend placement, hover formatting, number formatting for large balance sheet values.
- Accept: the chart looks intentional and readable on the paper background.

**6.4 Optional dark variant**
- Wire the palette swap so changing the dict in settings switches the full theme.
- Accept: the dark terminal variant renders cleanly with the same accents.

---

## Phase 7: Tests, docs, and deploy (2 to 3 hours)

**7.1 Tests**
- `tests/` for cache freshness, normalize and rebase, regime segments, correlation. Use small fixture Series, no live network in tests.
- Accept: `pytest` passes and covers the four processing and cache paths.

**7.2 README**
- Setup steps, FRED key instructions, run command, screenshot, deploy notes.
- Accept: a new user can clone, add a key, and run from the README alone.

**7.3 Deploy to Streamlit Community Cloud**
- Push to GitHub, connect the repo, add `FRED_API_KEY` to Cloud secrets.
- Accept: the public URL loads, all three regions render, the cache works on the host.

---

## Phase 8: UI elevation pass

See [TASKS_UI.md](TASKS_UI.md) — a detailed, task-by-task portfolio-grade UI
overhaul (hero header, KPI cards, chart finish, dark terminal variant, and more).

---

## Suggested build order

Phases run in sequence. Inside a phase, tasks can interleave. Build a thin vertical slice first: one region, FRED plus yfinance, one plain chart. Confirm the data pipeline before investing in the design pass. Save Phase 6 for last so polish lands on a working app.
