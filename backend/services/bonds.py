import re
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import StringIO
from datetime import datetime, date, timezone

import httpx
import pandas as pd
import yfinance as yf
from fastapi import HTTPException

BONDS = [
    {"ticker": "AU10Y", "name": "AU Government Bonds", "section": "bonds", "currency": "%", "maturity": "10Y", "source": "oecd",        "oecd_area": "AUS"},
    {"ticker": "UK10Y", "name": "UK Government Bonds", "section": "bonds", "currency": "%", "maturity": "10Y", "source": "oecd",        "oecd_area": "GBR"},
    {"ticker": "US10Y", "name": "US Government Bonds", "section": "bonds", "currency": "%", "maturity": "10Y", "source": "yf",          "yf_ticker": "^TNX"},
    {"ticker": "JP10Y", "name": "Japanese Govt Bonds", "section": "bonds", "currency": "%", "maturity": "10Y", "source": "oecd",        "oecd_area": "JPN"},
    {"ticker": "US5Y",  "name": "US 5Y Treasury",      "section": "bonds", "currency": "%", "maturity": "5Y",  "source": "yf",          "yf_ticker": "^FVX"},
    {"ticker": "US3Y",  "name": "US 3Y Treasury",      "section": "bonds", "currency": "%", "maturity": "3Y",  "source": "us_treasury", "treasury_tag": "BC_3YEAR"},
]

# How many calendar days to return for each period.
# No warmup needed — bonds use useWarmup=false on the frontend.
PERIOD_DAYS = {
    "1d":  90,
    "1w":  180,
    "1m":  365,
    "3m":  3 * 365,
    "1y":  5 * 365,
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
    """Fetch yield history from Yahoo Finance. ^TNX/^FVX etc. quote yield in % p.a."""
    hist = yf.Ticker(yf_ticker).history(period="5y", interval="1d")
    if hist.empty:
        raise ValueError(f"No yfinance data for {yf_ticker}")
    close = hist["Close"].dropna()
    close.index = pd.to_datetime(close.index).tz_localize(None)
    return close


def _fetch_one_treasury_month(ym: str, bc_tag: str) -> list[tuple]:
    """Fetch one month of US Treasury yield curve XML and extract (date, value) pairs."""
    url = (
        "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml"
        f"?data=daily_treasury_yield_curve&field_tdr_date_value_month={ym}"
    )
    timeout = httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=5.0)
    with httpx.Client(timeout=timeout, headers={"User-Agent": "Mozilla/5.0"}) as client:
        resp = client.get(url)
        resp.raise_for_status()

    result = []
    for entry in re.findall(r"<entry>.*?</entry>", resp.text, re.DOTALL):
        dt_m  = re.search(r"NEW_DATE[^>]*>(\d{4}-\d{2}-\d{2})", entry)
        val_m = re.search(rf"<d:{bc_tag}[^>]*>([^<]+)<", entry)
        if dt_m and val_m:
            try:
                result.append((pd.to_datetime(dt_m.group(1)), float(val_m.group(1))))
            except (ValueError, TypeError):
                pass
    return result


def _fetch_us_treasury(bc_tag: str) -> pd.Series:
    """
    Fetch 5 years of US Treasury daily yield data for a given maturity tag.
    Fetches the last 60 months in parallel (20 at a time) and combines.
    bc_tag: 'BC_3YEAR', 'BC_5YEAR', 'BC_10YEAR', etc.
    """
    from datetime import timedelta
    today = date.today()
    months = []
    d = today.replace(day=1)
    for _ in range(60):
        months.append(d.strftime("%Y%m"))
        d = (d - timedelta(days=1)).replace(day=1)  # step back one month

    records: dict[pd.Timestamp, float] = {}
    with ThreadPoolExecutor(max_workers=20) as pool:
        futures = {pool.submit(_fetch_one_treasury_month, ym, bc_tag): ym for ym in months}
        for future in as_completed(futures):
            try:
                for dt, val in future.result():
                    records[dt] = val
            except Exception:
                pass  # skip months that fail (e.g. future months with no data)

    if not records:
        raise ValueError(f"No US Treasury data for {bc_tag}")

    return pd.Series(records).sort_index()


def _fetch_oecd(area_code: str) -> pd.Series:
    """
    Fetch OECD long-term interest rate (IRLT) for a country, monthly, % p.a.
    OECD DF_FINMARK dataset; 9 dimensions, last 6 wildcarded.
    """
    url = (
        "https://sdmx.oecd.org/public/rest/data/"
        f"OECD.SDD.STES,DSD_STES@DF_FINMARK,4.0/"
        f"{area_code}.M.IRLT......?startPeriod=2010-01"
    )
    timeout = httpx.Timeout(connect=5.0, read=30.0, write=5.0, pool=5.0)
    with httpx.Client(timeout=timeout, headers={"User-Agent": "Mozilla/5.0"}) as client:
        resp = client.get(url)
        resp.raise_for_status()

    periods = re.findall(r'ObsDimension[^/]* value="(\d{4}-\d{2})"', resp.text)
    values  = re.findall(r'ObsValue value="([^"]+)"', resp.text)

    if not periods:
        raise ValueError(f"No OECD IRLT data for {area_code}")

    records: dict[pd.Timestamp, float] = {}
    for p, v in zip(periods, values):
        try:
            records[pd.to_datetime(p, format="%Y-%m")] = float(v)
        except (ValueError, TypeError):
            pass

    if not records:
        raise ValueError(f"Could not parse OECD data for {area_code}")

    return pd.Series(records).sort_index()


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

    if bond["source"] == "oecd":
        area = bond["oecd_area"]
        raw = _get_cached(f"oecd_{area}", lambda: _fetch_oecd(area))
        return _ffill_daily(raw)

    if bond["source"] == "us_treasury":
        tag = bond["treasury_tag"]
        raw = _get_cached(f"us_treasury_{tag}", lambda: _fetch_us_treasury(tag))
        return _ffill_daily(raw)

    raise ValueError(f"Unknown bond source: {bond['source']}")


def _fetch_bond_summary(bond: dict) -> dict:
    ticker = bond["ticker"]
    try:
        if bond["source"] == "yf":
            # fast_info avoids the heavy history() endpoint that gets rate-limited on cloud IPs
            fi     = yf.Ticker(bond["yf_ticker"]).fast_info
            price  = round(float(fi.last_price), 3) if fi.last_price else None
            prev   = fi.previous_close
            change = round(float(fi.last_price) - float(prev), 3) if fi.last_price and prev else None
        else:
            series = _get_yield_series(bond)
            price  = round(float(series.iloc[-1]), 3) if len(series) >= 1 else None
            change = round(float(series.iloc[-1]) - float(series.iloc[-2]), 3) if len(series) >= 2 else None
        return {
            "ticker":         ticker,
            "name":           bond["name"],
            "section":        bond["section"],
            "currency":       bond["currency"],
            "maturity":       bond["maturity"],
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
            "maturity":       bond["maturity"],
            "price":          None,
            "change_percent": None,
            "updated_at":     datetime.now(timezone.utc).isoformat(),
            "error":          str(exc),
        }


def get_bonds() -> list[dict]:
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
