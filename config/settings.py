"""Central configuration: series IDs, tickers, crisis windows, palette, constants."""

from datetime import date

# ── FRED central bank series ─────────────────────────────────────────────────

FRED_SERIES: dict[str, dict] = {
    "United States": {
        "series_id": "WALCL",
        "label": "Federal Reserve Total Assets",
        "cadence": "weekly",
        "currency": "USD",
        "unit": "Millions USD",
    },
    "Eurozone": {
        "series_id": "ECBASSETSW",
        "label": "ECB Total Assets",
        "cadence": "weekly",
        "currency": "EUR",
        "unit": "Millions EUR",
    },
    "Japan": {
        "series_id": "JPNASSETS",
        "label": "Bank of Japan Total Assets",
        "cadence": "monthly",
        "currency": "JPY",
        "unit": "Millions JPY",
    },
}

# ── Equity index tickers ──────────────────────────────────────────────────────

EQUITY_TICKERS: dict[str, dict] = {
    "United States": {
        "ticker": "^GSPC",
        "label": "S&P 500",
    },
    "Eurozone": {
        "ticker": "^STOXX50E",
        "label": "Euro Stoxx 50",
    },
    "Japan": {
        "ticker": "^N225",
        "label": "Nikkei 225",
    },
}

REGIONS: list[str] = list(FRED_SERIES.keys())

# ── Regime detection ──────────────────────────────────────────────────────────

REGIME_WINDOW_DAYS: int = 90

# ── Correlation windows ───────────────────────────────────────────────────────

CORRELATION_WINDOWS: list[int] = [30, 90, 360]

# ── Rebase ────────────────────────────────────────────────────────────────────

DEFAULT_BASELINE_YEAR: int = 2015

# ── Crisis bookmark windows ───────────────────────────────────────────────────

CRISIS_WINDOWS: dict[str, tuple[date, date]] = {
    "2008 Banking Collapse": (date(2008, 9, 1), date(2009, 6, 30)),
    "2020 Pandemic Surge": (date(2020, 2, 15), date(2020, 6, 30)),
    "2023 Regional Bank Stress": (date(2023, 3, 1), date(2023, 6, 30)),
    "Full History": (date(2004, 1, 1), date(2099, 12, 31)),  # sentinel max; clamp to data range at runtime
}

# ── Visual palette ────────────────────────────────────────────────────────────

PALETTE: dict[str, str] = {
    "background": "#F4F1E9",
    "panel": "#E9E3D6",
    "text": "#20232A",
    "brass": "#C68A2E",       # central bank line
    "verdigris": "#2E8B83",   # equity line
    "expansion": "#BFD8B8",   # regime shading fill
    "contraction": "#E3B4A4", # regime shading fill
    "muted": "#9A968C",
}

EXPANSION_OPACITY: float = 0.18
CONTRACTION_OPACITY: float = 0.18

# ── Cache ─────────────────────────────────────────────────────────────────────

CACHE_TTL_HOURS: int = 24
CACHE_DIR: str = "data/cache"
MANIFEST_FILENAME: str = "manifest.json"
