import time
import threading
from io import StringIO

import httpx
import pandas as pd
from fastapi import HTTPException

FRED_DGS2_URL        = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS2"
MULTPL_EARNINGS_URL  = "https://www.multpl.com/s-p-500-earnings-yield/table/by-month"

CACHE_TTL       = 3600
MAX_CHART_POINTS = 500

PERIOD_DAYS = {
    "1y":  365,
    "3y":  365 * 3,
    "5y":  365 * 5,
    "10y": 365 * 10,
    "max": None,
}

_cache: dict[str, tuple[float, object]] = {}
_locks: dict[str, threading.Lock] = {}
_locks_mutex = threading.Lock()


def _get_or_fetch(key: str, fn):
    with _locks_mutex:
        if key not in _locks:
            _locks[key] = threading.Lock()
    with _locks[key]:
        if key in _cache:
            fetched_at, data = _cache[key]
            if time.time() - fetched_at < CACHE_TTL:
                return data
        data = fn()
        _cache[key] = (time.time(), data)
        return data


def _fetch_all() -> pd.DataFrame:
    headers = {"User-Agent": "Mozilla/5.0"}
    with httpx.Client(timeout=30, headers=headers) as client:
        dgs2_resp   = client.get(FRED_DGS2_URL)
        multpl_resp = client.get(MULTPL_EARNINGS_URL)
        dgs2_resp.raise_for_status()
        multpl_resp.raise_for_status()

    # 2Y Treasury yield from FRED — CSV has columns DATE, DGS2
    dgs2 = pd.read_csv(StringIO(dgs2_resp.text), na_values=["."])
    dgs2.columns = ["date", "treasury_2y"]
    dgs2["date"] = pd.to_datetime(dgs2["date"])
    dgs2["treasury_2y"] = pd.to_numeric(dgs2["treasury_2y"], errors="coerce")
    dgs2 = dgs2.dropna().set_index("date")
    # Downsample daily → month-end to align with monthly earnings yield
    dgs2_monthly = dgs2["treasury_2y"].resample("ME").last().dropna()

    # S&P 500 earnings yield from multpl.com — HTML table with Date / Value columns
    tables = pd.read_html(StringIO(multpl_resp.text))
    ey = tables[0].copy()
    ey.columns = ["date", "earnings_yield"]
    ey["date"] = pd.to_datetime(ey["date"], format="mixed", errors="coerce")
    ey["earnings_yield"] = pd.to_numeric(
        ey["earnings_yield"].astype(str).str.replace("%", "").str.strip(),
        errors="coerce",
    )
    ey = ey.dropna().set_index("date")
    ey.index = ey.index + pd.offsets.MonthEnd(0)

    merged = pd.concat([dgs2_monthly, ey["earnings_yield"]], axis=1).dropna()
    merged["spread"] = merged["earnings_yield"] - merged["treasury_2y"]
    return merged.sort_index()


def _slice_period(df: pd.DataFrame, period: str) -> pd.DataFrame:
    days = PERIOD_DAYS.get(period)
    if days is None:
        return df
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=days)
    return df[df.index >= cutoff]


def _downsample(df: pd.DataFrame) -> pd.DataFrame:
    if len(df) <= MAX_CHART_POINTS:
        return df
    step = max(1, len(df) // MAX_CHART_POINTS)
    sampled = df.iloc[::step].copy()
    if sampled.index[-1] != df.index[-1]:
        sampled = pd.concat([sampled, df.iloc[[-1]]])
    return sampled


def get_yield_spread(period: str = "5y") -> list[dict]:
    try:
        merged = _get_or_fetch("yield_spread_all", _fetch_all)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Yield spread unavailable: {exc}")

    sliced = _downsample(_slice_period(merged, period))
    return [
        {
            "timestamp":      str(idx.date()),
            "treasury_2y":    round(float(row["treasury_2y"]),    3),
            "earnings_yield": round(float(row["earnings_yield"]), 3),
            "spread":         round(float(row["spread"]),         3),
        }
        for idx, row in sliced.iterrows()
    ]
