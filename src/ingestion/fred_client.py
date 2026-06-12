"""FRED REST API client — fetches a single series and returns a clean pandas Series."""

import os

import pandas as pd
import requests

FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"


def _get_api_key() -> str:
    """Read FRED API key from st.secrets (Streamlit Cloud) or environment/.env."""
    try:
        import streamlit as st

        return st.secrets["FRED_API_KEY"]
    except Exception:
        pass

    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    key = os.getenv("FRED_API_KEY")
    if not key:
        raise ValueError("FRED_API_KEY not found in st.secrets or environment")
    return key


def fetch_series(series_id: str, start_date: str = "2004-01-01") -> pd.Series:
    """
    Fetch a FRED series and return a clean pandas Series.

    Converts "." missing-value markers to NaN. Dates are timezone-naive.
    Values are float64, sorted ascending by date.

    Args:
        series_id: FRED series ID (e.g. "WALCL").
        start_date: ISO date string for observation_start.

    Returns:
        pandas Series with DatetimeIndex, name set to series_id.

    Raises:
        requests.HTTPError: on non-2xx responses.
        ValueError: if FRED_API_KEY is missing.
    """
    api_key = _get_api_key()
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": start_date,
    }
    response = requests.get(FRED_BASE_URL, params=params, timeout=30)
    response.raise_for_status()

    observations = response.json().get("observations", [])

    dates = [obs["date"] for obs in observations]
    values = [
        float("nan") if obs.get("value", ".") == "." else float(obs["value"])
        for obs in observations
    ]

    series = pd.Series(
        data=values,
        index=pd.to_datetime(dates),
        name=series_id,
        dtype="float64",
    )
    series.index = series.index.tz_localize(None)
    return series.sort_index()
