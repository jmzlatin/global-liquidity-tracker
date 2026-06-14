# CLAUDE.md

Persistent context for Claude Code. Read this before writing any code.

## Project: Global Market Liquidity & Central Bank Tracker

A Streamlit app that pulls central bank balance sheet data and regional equity indices, aligns the two on a shared timeline, and renders the relationship as interactive dual-axis charts. The app loads fast and asks the user for almost no configuration. Pick a region, see the chart.

**Dual-frontend (tandem).** The app runs as **two independent frontends over one
shared Python backend, permanently** — the original Streamlit app *and* a
Next.js/Vercel app. Both import the same pure `src/processing` + `src/ingestion`
modules; a backend change affects both. This is a tandem architecture, **not** a
migration/cutover — Streamlit is kept, not decommissioned. See
`docs/adr/0001-vercel-migration.md` (the authority on this) and `TASKS_VERCEL.md`.

## Tech stack

**Shared backend (both frontends use this):**

- Python 3.11+
- pandas + numpy for processing
- requests for the FRED REST API
- yfinance for equity index data
- pytest for tests
- ruff for lint and format

**Streamlit frontend:**

- Streamlit for the UI
- Plotly for interactive dual-axis charts and background shading
- python-dotenv for secrets (local); `st.secrets` on Streamlit Cloud

**Vercel/Next.js frontend:**

- Next.js (App Router) + TypeScript
- `react-plotly.js` for the charts (keep visual parity with the Streamlit Plotly figures)
- Python serverless functions under `api/` that reuse the shared backend
- Vercel KV (Upstash Redis) for the serverless cache; `os.environ` for secrets

Do not mix Dash in. Within each frontend, do not introduce a second UI framework.

## Hosting

Two deploy targets, one repo, no runtime conflict — each platform builds only its half.

- **Streamlit Community Cloud** — entry point `app.py` at the repo root; FRED key in Streamlit Cloud secrets.
- **Vercel** — single-root project (Root Directory = repo root). `vercel.json` pins the `@vercel/python` builder to `api/*.py` so Vercel ignores the Streamlit `app.py`. FRED key + KV vars in Vercel env vars. The Next.js app and `api/` functions are the Vercel half.

Neither key goes in the repo.

## Repo structure

```
global-liquidity-tracker/
  CLAUDE.md
  README.md
  requirements.txt       # FAT set — Streamlit Cloud installs from this
  vercel.json            # pins @vercel/python to api/*.py; ignores app.py
  .env.example
  .gitignore
  .streamlit/
    config.toml          # theme
    secrets.toml         # local only, gitignored
  app.py                 # Streamlit entry, thin orchestration only
  api/                   # Vercel Python serverless functions
    requirements.txt     # SLIM set — serverless deps only (no streamlit/plotly)
    ping.py              # Phase 0 feasibility spike (throwaway)
    series.py            # main data endpoint (Phase 2; reuses src/)
  web/                   # Next.js frontend (Phase 1+): app/, components/, lib/, styles/
  config/
    settings.py          # series IDs, tickers, crisis windows, palette, constants
  TASKS_UI.md            # UI elevation task plan
  TASKS_VERCEL.md        # Vercel/Next.js frontend task plan
  docs/
    adr/                 # architecture decision records (0001 = tandem)
  src/                   # SHARED backend — imported by BOTH frontends
    ingestion/
      fred_client.py     # FRED REST calls
      equity_client.py   # yfinance wrapper
      cache.py           # 24h local cache read/write
    processing/
      normalize.py       # merge, forward-fill, rebase to 100
      regimes.py         # 90-day slope, expansion/contraction segments
      correlation.py     # rolling 30/90/360 correlation
      summary.py         # KpiSummary dataclass; computes KPIs from processed data
    ui/
      theme.py           # CSS injection, animations, Plotly template
      charts.py          # dual-axis chart builder, regime shading
      components.py      # sidebar, metric grid, crisis buttons
  data/
    cache/               # gitignored, runtime cache files
  tests/
    test_cache.py
    test_normalize.py
    test_regimes.py
    test_correlation.py
    test_summary.py
```

## Layer boundaries (enforce these)

- The UI layer never calls an external API. UI calls processing, processing calls ingestion, ingestion calls the network.
- `app.py` stays thin. No business logic in the entry file. Wire components and call into `src/`.
- Each module does one job. Keep functions small and typed.
- **`src/processing/*` and the pure parts of `src/ingestion/*` stay framework-free** — no `streamlit`, `plotly`, `st.*`, or Vercel/Next imports. This is what lets both frontends import them. The Streamlit-only code lives in `src/ui/*` and `app.py`; the Vercel-only code lives in `api/` and `web/`. Never import a frontend or a platform-specific store from the shared backend.

## Data sources

### Central bank balance sheets (FRED REST API)

Free developer key required. Endpoint pattern:

```
https://api.stlouisfed.org/fred/series/observations
  ?series_id=WALCL
  &api_key=YOUR_KEY
  &file_type=json
```

| Region | Bank | Series ID | Cadence | Note |
|---|---|---|---|---|
| United States | Federal Reserve | `WALCL` | Weekly, Wednesday | Millions USD |
| Eurozone | ECB | `ECBASSETSW` | Weekly | Local currency, EUR base |
| Japan | BOJ | `JPNASSETS` | Monthly | Local currency, JPY base |

Verify each series unit and frequency on first fetch. Do not assume the three share a unit or currency. The app compares trends and percentage change, not raw cross-currency totals.

### Equity baselines (yfinance)

No key. Use `yf.download(ticker, start, end)` and take the Close column.

| Region | Index | Ticker |
|---|---|---|
| United States | S&P 500 | `^GSPC` |
| Eurozone | Euro Stoxx 50 | `^STOXX50E` |
| Japan | Nikkei 225 | `^N225` |

yfinance gotcha: recent versions return MultiIndex columns for single tickers. Flatten to a single Close series before returning from `equity_client.py`.

## Environment

`.env` holds `FRED_API_KEY`. Provide `.env.example`:

```
FRED_API_KEY=your_key_here
```

Load with python-dotenv locally. On Streamlit Cloud read from `st.secrets`. On Vercel read from `os.environ` (set `FRED_API_KEY` plus the KV connection vars in the Vercel project). The shared `fred_client` reads the key in a frontend-agnostic way; never hardcode a `st.secrets`-only path into the shared backend. Never commit `.env` or `secrets.toml`. Add both to `.gitignore`.

## Caching rules

Goal: avoid FRED and yfinance rate limits and load instantly on repeat runs.

The cache is the **one part of the backend that is genuinely dual, not shared**:
the same 24h-freshness + stale-fallback *contract*, two *implementations* behind
one interface (`fetched_at` freshness check, `stale` flag on fetch failure).
Keep the contract identical so the shared compute never knows which store it got.

- **Streamlit (filesystem store):**
  - On startup, check `data/cache/` for the requested series file.
  - Store each series as a CSV plus a `manifest.json` recording `fetched_at` per series.
  - If `fetched_at` is under 24 hours old, read the local CSV. Skip the network.
  - If stale or missing, fetch, overwrite the CSV, update the manifest.
- **Vercel (Vercel KV / Upstash Redis store):** the serverless filesystem is
  ephemeral and read-only outside `/tmp`, so the CSV/manifest design cannot work.
  Use one KV key per series storing `{fetched_at, payload}`; same 24h freshness,
  same refetch-on-stale, same stale-fallback.
- **Both:** if a live fetch fails, fall back to the stale cached value and surface
  a small warning (`st.warning` / a `stale: true` flag in the API payload). Never
  crash on a network error.

## Processing rules

- Build one daily `DatetimeIndex` spanning the union of all series dates.
- Reindex every series onto the daily index.
- Forward-fill empty entries. Weekly and monthly central bank values carry forward until the next print. Equity gaps on weekends fill forward.
- Rebase mode: index a series to 100 at the first observation of a chosen baseline year, then express every later point as a percentage of that baseline. Use rebase for clean multi-series comparison.
- Dual-axis mode: primary y-axis is the central bank asset level, secondary y-axis is the equity index. This is the default view.
- Provide a toggle between raw dual-axis and rebased single-axis.

## Regime shading logic

- Operate on the central bank series resampled to a regular frequency.
- Over a rolling 90-day window, fit a simple slope (linear regression slope or the difference of endpoints of a rolling mean). Positive slope is expansion, negative is contraction.
- Collapse consecutive same-sign days into contiguous segments.
- Render each segment as a Plotly `vrect` behind the lines. Soft sage for expansion, soft clay for contraction. Keep opacity low so the lines stay readable.

## Correlation panel

- Align the central bank series and the equity series on the daily index.
- Compute `pct_change()` on each.
- Compute `rolling(window).corr()` for windows 30, 90, 360.
- Show the latest value of each window in a metric grid. Color positive and negative coefficients differently. Show the rolling correlation as a small line chart under the main chart.
- Watch for alignment after forward-fill. Correlation on a constant carried-forward stretch returns NaN or noise. Drop NaN before reporting.

## Crisis bookmark windows

Define in `config/settings.py` as constants. A button sets the chart date range and reruns.

| Label | Start | End |
|---|---|---|
| 2008 banking collapse | 2008-09-01 | 2009-06-30 |
| 2020 pandemic surge | 2020-02-15 | 2020-06-30 |
| 2023 regional bank stress | 2023-03-01 | 2023-06-30 |
| Full history | min date | max date |

## KPI summary module

`src/processing/summary.py` exposes `KpiSummary`, a frozen dataclass computed from the processed dataframe and analysis results. It lives in the processing layer — not the UI — so the UI just reads `.cb_latest`, `.eq_change_90d_pct`, etc. without doing any math itself.

Fields: `cb_latest`, `cb_change_90d_pct`, `eq_latest`, `eq_change_90d_pct`, `regime_label`, `peak_correlation`. All floats or strings; no Streamlit or Plotly imports allowed in this module.

## Design direction

The UI elevation pass is complete. The app now reads as a designed financial terminal on warm paper. Do not revert toward Streamlit defaults.

**Both frontends share this design language.** The palette, typography, animations,
and dual-axis/regime-shading look below are the source of truth for the Streamlit
UI (`src/ui/*`, `.streamlit/config.toml`) *and* for the Vercel/Next.js UI, which
reproduces them in CSS/Tailwind + `react-plotly.js` (Phase 6 of `TASKS_VERCEL.md`).
Keep one Plotly template per frontend, mirroring the same palette — never set
colors ad-hoc on either side.

Palette "Brass and Verdigris on Paper":

| Role | Hex |
|---|---|
| Paper background | `#F4F1E9` |
| Panel / secondary background | `#E9E3D6` |
| Ink text | `#20232A` |
| Primary accent (central bank line) | `#C68A2E` (brass) |
| Equity line | `#2E8B83` (verdigris) |
| Expansion shade | `#BFD8B8` at ~0.18 opacity |
| Contraction shade | `#E3B4A4` at ~0.18 opacity |
| Muted grid / labels | `#9A968C` |

`.streamlit/config.toml`:

```toml
[theme]
base = "light"
primaryColor = "#C68A2E"
backgroundColor = "#F4F1E9"
secondaryBackgroundColor = "#E9E3D6"
textColor = "#20232A"
font = "serif"
```

Typography and CSS — implemented in `ui/theme.py`:

- Fraunces (warm serif) for headings, IBM Plex Sans for body, IBM Plex Mono for metric values.
- CSS animations: `fadeUp`, `fadeIn`, `drawRule`, `pulse`, `breathe`, `sheen` — applied to headers, metric cards, and buttons. Do not remove these.
- Radial gradient background wash (brass top-left, verdigris top-right) on the app root.
- Rounded corners, `#9A968C` hairline borders, generous padding on all panels.
- Crisis bookmark buttons styled with brass fill on active/hover.
- One Plotly template in `ui/theme.py` (`build_plotly_template()`) applied to every figure. Never set Plotly colors or fonts ad-hoc — update the template instead.
- Central bank asset values displayed in trillions (divide raw millions by 1,000,000) with explicit "T" suffix on axis labels.

Optional second theme: a dark "terminal" variant on `#16181D` with the same brass and verdigris accents. `config/settings.py` holds `PALETTE`; swapping that dict switches the whole look.

## Commands

```bash
# install (shared backend + Streamlit frontend)
pip install -r requirements.txt

# run the Streamlit frontend locally
streamlit run app.py

# run the Vercel frontend locally (Next.js + Python /api)
vercel dev

# tests / lint (shared backend)
pytest
ruff check .
ruff format .
```

## requirements.txt (two sets, single root)

Root `requirements.txt` is the **fat** set — Streamlit Cloud installs from it:

```
streamlit
plotly
pandas
numpy
requests
yfinance
python-dotenv
pytest
ruff
```

`api/requirements.txt` is the **slim** set — what the Vercel function bundles
(keeps `streamlit`/`plotly` out of the serverless bundle):

```
pandas
numpy
requests
yfinance
```

## Conventions

- Type hints on every function signature.
- Short docstrings stating purpose, inputs, output.
- Keep functions under about 40 lines. Split when longer.
- Cache expensive Streamlit work with `@st.cache_data` on the data-loading functions, keyed by region and date range.
- No bare `except`. Catch specific errors and log a clear message.

## Known gotchas

- yfinance MultiIndex columns on single tickers. Flatten before returning.
- FRED returns `"."` for missing observations. Convert to NaN, then forward-fill.
- FRED dates are strings. Parse to timezone-naive datetimes. Keep equity dates timezone-naive too so joins line up.
- Forward-filled stretches produce flat segments. Account for this in both regime slope and correlation.
- Streamlit reruns top to bottom on every interaction. Keep heavy work behind the cache.
