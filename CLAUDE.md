# CLAUDE.md

Persistent context for Claude Code. Read this before writing any code.

## Project: Global Market Liquidity & Central Bank Tracker

A Streamlit app that pulls central bank balance sheet data and regional equity indices, aligns the two on a shared timeline, and renders the relationship as interactive dual-axis charts. The app loads fast and asks the user for almost no configuration. Pick a region, see the chart.

## Tech stack

- Python 3.11+
- Streamlit for the UI
- Plotly for interactive dual-axis charts and background shading
- pandas + numpy for processing
- requests for the FRED REST API
- yfinance for equity index data
- python-dotenv for secrets
- pytest for tests
- ruff for lint and format

Alternative: Dash works too, but this repo targets Streamlit. Do not mix both.

## Hosting

Public GitHub repo deployed to Streamlit Community Cloud. The app entry point is `app.py` at the repo root. The FRED key goes in Streamlit Cloud secrets, not the repo.

## Repo structure

```
global-liquidity-tracker/
  CLAUDE.md
  README.md
  requirements.txt
  .env.example
  .gitignore
  .streamlit/
    config.toml          # theme
    secrets.toml         # local only, gitignored
  app.py                 # Streamlit entry, thin orchestration only
  config/
    settings.py          # series IDs, tickers, crisis windows, palette, constants
  src/
    ingestion/
      fred_client.py     # FRED REST calls
      equity_client.py   # yfinance wrapper
      cache.py           # 24h local cache read/write
    processing/
      normalize.py       # merge, forward-fill, rebase to 100
      regimes.py         # 90-day slope, expansion/contraction segments
      correlation.py     # rolling 30/90/360 correlation
    ui/
      theme.py           # CSS injection, Plotly template
      charts.py          # dual-axis chart builder, regime shading
      components.py      # sidebar, metric grid, crisis buttons
  data/
    cache/               # gitignored, runtime cache files
  tests/
    test_cache.py
    test_normalize.py
    test_regimes.py
    test_correlation.py
```

## Layer boundaries (enforce these)

- The UI layer never calls an external API. UI calls processing, processing calls ingestion, ingestion calls the network.
- `app.py` stays thin. No business logic in the entry file. Wire components and call into `src/`.
- Each module does one job. Keep functions small and typed.

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

Load with python-dotenv locally. On Streamlit Cloud read from `st.secrets`. Never commit `.env` or `secrets.toml`. Add both to `.gitignore`.

## Caching rules

Goal: avoid FRED and yfinance rate limits and load instantly on repeat runs.

- On startup, check `data/cache/` for the requested series file.
- Store each series as a CSV plus a `manifest.json` recording `fetched_at` per series.
- If `fetched_at` is under 24 hours old, read the local CSV. Skip the network.
- If stale or missing, fetch, overwrite the CSV, update the manifest.
- If a live fetch fails, fall back to the stale cache and surface a small warning in the UI. Never crash on a network error.

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

## Design direction

Do not ship the default Streamlit look. No wall of blue. The target feel is a quiet financial terminal printed on warm paper, with brass and verdigris as the two data colors.

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

Typography and finish, applied through CSS injection in `ui/theme.py`:

- Headings in a warm serif. Load Fraunces or Spectral from Google Fonts via an injected `<link>`.
- Body in a clean sans. IBM Plex Sans works well with the palette.
- Metric values in a monospace face (IBM Plex Mono) for the terminal feel.
- Rounded corners on panels, a thin `#9A968C` hairline border, generous padding.
- Custom button styling: brass fill on hover, ink text, no default Streamlit red.
- Build one Plotly template in `ui/theme.py` and apply it to every figure so colors, fonts, and grid lines stay consistent.

Optional second theme: a dark "terminal" variant on `#16181D` with the same brass and verdigris accents. Build the app so swapping the palette dict in `config/settings.py` switches the whole look.

## Commands

```bash
# install
pip install -r requirements.txt

# run locally
streamlit run app.py

# tests
pytest

# lint and format
ruff check .
ruff format .
```

## requirements.txt

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
