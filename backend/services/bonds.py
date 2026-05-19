import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import StringIO
from datetime import datetime, timezone

import httpx
import pandas as pd
import yfinance as yf
from fastapi import HTTPException

BONDS = [
    {"ticker": "AU10Y",    "name": "AU Government Bonds",       "section": "bonds", "currency": "%", "source": "rba",   "rba_col": "cgs"},
    {"ticker": "AUTIB10Y", "name": "AU Treasury Indexed Bonds", "section": "bonds", "currency": "%", "source": "rba",   "rba_col": "tib"},
    {"ticker": "US10Y",    "name": "US Government Bonds",       "section": "bonds", "currency": "%", "source": "yf",    "yf_ticker": "^TNX"},
    {"ticker": "JP10Y",    "name": "Japanese Govt Bonds",       "section": "bonds", "currency": "%", "source": "fred",  "fred_id": "IRLTLT01JPM156N"},
]

# How many calendar days to return for each period.
# No warmup needed — bonds use useWarmup=false on the frontend.
# Periods return enough data that BB(20) has sufficient seed points.
PERIOD_DAYS = {
    "1d":        90,
    "1w":        180,
    "1m":        365,
    "3m":        3 * 365,
    "1y":        5 * 365,
    "1d_warmup":  90,
    "1w_warmup":  180,
    "1m_warmup":  365,
    "3m_warmup":  3 * 365,
    "1y_warmup":  5 * 365,
}

CACHE_TTL   = 3600  # 1 hour for successful fetches
FAILURE_TTL = 60    # 60 s for failed fetches — avoids serial retries on cold start

_FAILURE = object()  # sentinel stored in cache on fetch failure

_cache: dict[str, tuple[float, object]] = {}
_locks: dict[str, threading.Lock] = {}
_locks_mutex = threading.Lock()


def _get_cached(key: str, fn):
    with _locks_mutex:
        if key not in _locks:
            _locks[key] = threading.Lock()
    with _locks[key]:
        if key in _cache:
            fetched_at, data = _cache[key]
            ttl = FAILURE_TTL if data is _FAILURE else CACHE_TTL
            if time.time() - fetched_at < ttl:
                if data is _FAILURE:
                    raise RuntimeError(f"Cached fetch failure: {key}")
                return data
        try:
            data = fn()
            _cache[key] = (time.time(), data)
            return data
        except Exception:
            _cache[key] = (time.time(), _FAILURE)
            raise


def _fetch_yf(yf_ticker: str) -> pd.Series:
    """Fetch yield history from Yahoo Finance. ^TNX etc. quote yield in % p.a."""
    hist = yf.Ticker(yf_ticker).history(period="10y", interval="1d")
    if hist.empty:
        raise ValueError(f"No yfinance data for {yf_ticker}")
    close = hist["Close"].dropna()
    close.index = pd.to_datetime(close.index).tz_localize(None)
    return close


def _fetch_fred(series_id: str) -> pd.Series:
    """Fetch a FRED series CSV and return a daily DatetimeIndex Series (% p.a.)."""
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    # Split timeout: 5 s to connect, 30 s to read (FRED is slow on some hosts)
    timeout = httpx.Timeout(connect=5.0, read=30.0, write=5.0, pool=5.0)
    with httpx.Client(timeout=timeout, headers={"User-Agent": "Mozilla/5.0"}) as client:
        resp = client.get(url)
        resp.raise_for_status()

    df = pd.read_csv(StringIO(resp.text), na_values=["."])
    df.columns = ["date", "value"]
    df["date"]  = pd.to_datetime(df["date"], errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna().set_index("date").sort_index()
    return df["value"]


def _fetch_rba() -> dict[str, pd.Series | None]:
    """
    Fetch RBA Table F16 (Capital Market Yields – Government Bonds, monthly).
    Returns {"cgs": Series, "tib": Series} — both in % p.a.
    Falls back gracefully: missing columns return None.
    """
    url = "https://www.rba.gov.au/statistics/tables/csv/f16.csv"
    with httpx.Client(timeout=15, headers={"User-Agent": "Mozilla/5.0"}) as client:
        resp = client.get(url)
        resp.raise_for_status()

    text = resp.text
    # Reject HTML responses (wrong URL / redirect)
    if text.lstrip().startswith("<"):
        raise ValueError("RBA returned HTML instead of CSV")

    lines = text.splitlines()
    if not lines:
        raise ValueError("Empty RBA CSV response")

    # Row 0: Series IDs. Row 1: Titles. Data rows: date strings like "Mar-1969" or "Mar 1969".
    header_ids    = [c.strip() for c in lines[0].split(",")]
    header_titles = [c.strip().lower() for c in lines[1].split(",")] if len(lines) > 1 else []

    cgs_col = None
    tib_col = None

    # Search by series ID first
    for i, sid in enumerate(header_ids):
        sid_upper = sid.upper()
        if "FCMYGBAG10" in sid_upper:
            cgs_col = i
        elif "FCMYTIB10" in sid_upper:
            tib_col = i

    # Fall back: search by title
    if cgs_col is None or tib_col is None:
        for i, title in enumerate(header_titles):
            if "10" in title and "indexed" not in title and "bond" in title and cgs_col is None:
                cgs_col = i
            elif "10" in title and "indexed" in title and tib_col is None:
                tib_col = i

    # Parse data rows (skip header/metadata, find lines that start with a date)
    records: list[dict] = []
    for line in lines[1:]:
        parts = [p.strip() for p in line.split(",")]
        if not parts or not parts[0]:
            continue
        # Try several date formats used by the RBA
        date = None
        for fmt in ("%b-%Y", "%b %Y", "%B-%Y", "%B %Y"):
            try:
                date = pd.to_datetime(parts[0], format=fmt)
                break
            except ValueError:
                pass
        if date is None:
            try:
                date = pd.to_datetime(parts[0])
            except Exception:
                continue

        def _safe(col):
            if col is None or col >= len(parts) or not parts[col]:
                return None
            try:
                return float(parts[col])
            except ValueError:
                return None

        cgs_val = _safe(cgs_col)
        tib_val = _safe(tib_col)
        if cgs_val is not None or tib_val is not None:
            records.append({"date": date, "cgs": cgs_val, "tib": tib_val})

    if not records:
        raise ValueError("No data rows found in RBA F16 CSV")

    df = pd.DataFrame(records).set_index("date").sort_index()
    cgs = df["cgs"].dropna() if cgs_col is not None else None
    tib = df["tib"].dropna() if tib_col is not None else None
    return {"cgs": cgs, "tib": tib}


def _ffill_daily(series: pd.Series) -> pd.Series:
    """Forward-fill a Series to daily frequency up to today."""
    if series is None or len(series) == 0:
        return pd.Series(dtype=float)
    today = pd.Timestamp.today().normalize()
    idx = pd.date_range(series.index.min().normalize(), today, freq="D")
    return series.reindex(idx, method="ffill").dropna()


def _get_yield_series(bond: dict) -> pd.Series:
    """Return a daily DatetimeIndex Series of yield values (% p.a.) for the bond."""
    if bond["source"] == "yf":
        raw = _get_cached(f"yf_{bond['yf_ticker']}", lambda: _fetch_yf(bond["yf_ticker"]))
        return _ffill_daily(raw)

    if bond["source"] == "fred":
        raw = _get_cached(f"fred_{bond['fred_id']}", lambda: _fetch_fred(bond["fred_id"]))
        return _ffill_daily(raw)

    # RBA source — try live fetch, fall back to FRED nominal AU yield
    try:
        rba = _get_cached("rba_f16", _fetch_rba)
        raw = rba.get(bond["rba_col"])
        if raw is None or len(raw) == 0:
            raise ValueError("RBA column unavailable")
        return _ffill_daily(raw)
    except Exception:
        # Fallback: Australian nominal 10Y from FRED
        raw = _get_cached("fred_IRLTLT01AUM156N", lambda: _fetch_fred("IRLTLT01AUM156N"))
        return _ffill_daily(raw)


def _fetch_bond_summary(bond: dict) -> dict:
    ticker = bond["ticker"]
    try:
        series = _get_yield_series(bond)
        price  = round(float(series.iloc[-1]), 3) if len(series) >= 1 else None
        change = round(float(series.iloc[-1]) - float(series.iloc[-2]), 3) if len(series) >= 2 else None
        return {
            "ticker":         ticker,
            "name":           bond["name"],
            "section":        bond["section"],
            "currency":       bond["currency"],
            "price":          price,
            "change_percent": change,
            "updated_at":     datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        return {
            "ticker":         ticker,
            "name":           bond["name"],
            "section":        bond["section"],
            "currency":       bond["currency"],
            "price":          None,
            "change_percent": None,
            "updated_at":     datetime.now(timezone.utc).isoformat(),
            "error":          str(exc),
        }


def get_bonds() -> list[dict]:
    # Pre-warm the shared RBA cache so both AU bonds don't race-and-retry it.
    # On failure the sentinel is cached, so workers skip the retry immediately.
    rba_bonds = [b for b in BONDS if b["source"] == "rba"]
    if rba_bonds:
        try:
            _get_cached("rba_f16", _fetch_rba)
        except Exception:
            pass

    order = {b["ticker"]: i for i, b in enumerate(BONDS)}
    with ThreadPoolExecutor(max_workers=len(BONDS)) as pool:
        futures = {pool.submit(_fetch_bond_summary, bond): bond["ticker"] for bond in BONDS}
        results = [None] * len(BONDS)
        for future in as_completed(futures):
            ticker = futures[future]
            results[order[ticker]] = future.result()
    return results


def get_bond_history(ticker: str, period: str = "1m") -> list[dict]:
    bond = next((b for b in BONDS if b["ticker"] == ticker), None)
    if bond is None:
        raise HTTPException(status_code=404, detail=f"Bond ticker '{ticker}' not found")

    try:
        series = _get_yield_series(bond)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Bond data unavailable: {exc}")

    days   = PERIOD_DAYS.get(period, 365)
    cutoff = pd.Timestamp.today() - pd.Timedelta(days=days)
    series = series[series.index >= cutoff]

    return [
        {
            "timestamp": idx.isoformat(),
            "open":  round(float(val), 3),
            "high":  round(float(val), 3),
            "low":   round(float(val), 3),
            "close": round(float(val), 3),
        }
        for idx, val in series.items()
    ]
