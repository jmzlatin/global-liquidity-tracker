"""yfinance equity index client — wraps yf.download and returns a flat Close series."""

import pandas as pd
import yfinance as yf


def fetch_equity(ticker: str, start_date: str = "2004-01-01") -> pd.Series:
    """
    Download equity close prices for a single ticker.

    Flattens MultiIndex columns produced by recent yfinance versions.
    Returns a timezone-naive Series sorted ascending by date.

    Args:
        ticker: Yahoo Finance ticker symbol (e.g. "^GSPC").
        start_date: ISO date string for download start.

    Returns:
        pandas Series with timezone-naive DatetimeIndex, name set to ticker.

    Raises:
        ValueError: if the downloaded data contains no Close column.
    """
    raw = yf.download(ticker, start=start_date, progress=False, auto_adjust=True)

    if raw.empty:
        raise ValueError(f"No data returned for ticker {ticker!r}")

    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)

    if "Close" not in raw.columns:
        raise ValueError(f"No 'Close' column found for ticker {ticker!r}")

    close: pd.Series = raw["Close"].rename(ticker)

    if close.index.tz is not None:
        close.index = close.index.tz_convert("UTC").tz_localize(None)
    else:
        close.index = pd.to_datetime(close.index)

    return close.sort_index().dropna()
