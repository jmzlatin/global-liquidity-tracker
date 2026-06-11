# Global Market Liquidity & Central Bank Tracker

A Streamlit app that pulls central bank balance-sheet data and regional equity
indices, aligns the two on a shared daily timeline, and renders the relationship
as interactive dual-axis charts with regime shading and rolling correlation.

Pick a region, see the chart. The app caches everything locally so repeat runs
load instantly and stay under FRED and yfinance rate limits.

## Features

- **Dual-axis chart** — central bank total assets (brass) against the regional
  equity index (verdigris), each on its own scale.
- **Rebased view** — normalize both series to 100 at a baseline year for a clean
  percentage-change comparison.
- **Regime shading** — a rolling 90-day slope classifies balance-sheet
  *expansion* (sage) vs *contraction* (clay), drawn as bands behind the lines.
- **Rolling correlation panel** — 30 / 90 / 360-day coefficients in a metric grid
  plus a rolling-correlation line chart.
- **Crisis bookmarks** — one click jumps the date range to the 2008 banking
  collapse, the 2020 pandemic surge, the 2023 regional-bank stress, or full
  history.
- **Resilient caching** — 24-hour local CSV cache with stale-fallback, so a
  network blip never crashes the app.

## Regions & data sources

| Region | Central bank (FRED) | Equity index (yfinance) |
|---|---|---|
| United States | Federal Reserve Total Assets — `WALCL` | S&P 500 — `^GSPC` |
| Eurozone | ECB Total Assets — `ECBASSETSW` | Euro Stoxx 50 — `^STOXX50E` |
| Japan | Bank of Japan Total Assets — `JPNASSETS` | Nikkei 225 — `^N225` |

Central bank series are in local currency (USD / EUR / JPY millions). The app
compares trends and percentage change, not raw cross-currency totals.

## Requirements

- Python 3.11+
- A free [FRED API key](https://fred.stlouisfed.org/docs/api/api_key.html)
  (no key is needed for the yfinance equity data)

## Setup

```bash
# 1. Clone
git clone https://github.com/jmzlatin/global-liquidity-tracker.git
cd global-liquidity-tracker

# 2. (Recommended) create a virtual environment
python -m venv .venv && source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your FRED key
cp .env.example .env
# then edit .env and set FRED_API_KEY=your_real_key
```

The key is read from `st.secrets["FRED_API_KEY"]` when present (Streamlit Cloud)
and otherwise from the `FRED_API_KEY` environment variable / local `.env`.

## Run

```bash
streamlit run app.py
```

The app opens at <http://localhost:8501>. Pick a region from the sidebar; the
first load fetches from FRED and yfinance, and subsequent loads within 24 hours
read the local cache in `data/cache/`.

## Tests, lint, format

```bash
pytest             # unit tests — cache, normalize/rebase, regimes, correlation
ruff check .       # lint
ruff format .      # format
```

Tests use small fixture Series and never hit the network.

## Project layout

```
app.py                 # Streamlit entry, thin orchestration
config/settings.py     # series IDs, tickers, crisis windows, palette, constants
src/
  ingestion/           # FRED client, yfinance wrapper, 24h cache layer
  processing/          # merge/ffill, rebase, regime slope, rolling correlation
  ui/                  # theme/CSS, chart builders, sidebar & components
tests/                 # pytest suite over the processing and cache paths
```

The UI layer never calls an external API: UI → processing → ingestion → network.

## Deploy to Streamlit Community Cloud

1. Push this repo to a public GitHub repository.
2. At <https://share.streamlit.io>, create a new app pointing at `app.py`.
3. In the app's **Settings → Secrets**, add:
   ```toml
   FRED_API_KEY = "your_real_key"
   ```
4. Deploy. All three regions render on the public URL; the cache works on the
   host. Never commit `.env` or `.streamlit/secrets.toml` — both are gitignored.

## License

See [LICENSE](LICENSE).

---

Developed by Jordan M. Zlatin.
