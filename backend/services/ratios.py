import os
import time
import threading
from io import StringIO

import httpx
import pandas as pd
import yfinance as yf
from fastapi import HTTPException

GOLD_OZ_OUTSTANDING = 6_836_000_000  # estimated total above-ground gold (troy oz)
CACHE_TTL = 3600  # 1 hour

FRED_BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv"
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


def _fred_csv(series_id: str) -> pd.DataFrame:
    with httpx.Client(timeout=30) as client:
        r = client.get(FRED_BASE, params={"id": series_id})
        r.raise_for_status()
    df = pd.read_csv(StringIO(r.text), parse_dates=["DATE"])
    df.columns = ["date", "value"]
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["value"]).set_index("date")
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    return df


def _downsample(df: pd.DataFrame) -> pd.DataFrame:
    if len(df) <= MAX_CHART_POINTS:
        return df
    step = max(1, len(df) // MAX_CHART_POINTS)
    sampled = df.iloc[::step].copy()
    if len(df) > 0 and (len(sampled) == 0 or sampled.index[-1] != df.index[-1]):
        sampled = pd.concat([sampled, df.iloc[[-1]]])
    return sampled


def _slice(df: pd.DataFrame, period: str) -> pd.DataFrame:
    days = PERIOD_DAYS.get(period)
    if days is None:
        return df
    cutoff = pd.Timestamp.now(tz=None) - pd.Timedelta(days=days)
    return df[df.index >= cutoff]


def _fetch_buffett_all() -> pd.DataFrame:
    wilshire = _fred_csv("WILL5000INDFC").rename(columns={"value": "wilshire"})
    gdp = _fred_csv("GDP").rename(columns={"value": "gdp"})
    gdp_daily = gdp.resample("D").ffill()
    merged = wilshire.copy()
    merged["gdp"] = gdp_daily.reindex(merged.index)["gdp"].ffill()
    merged = merged.dropna()
    merged["ratio"] = (merged["wilshire"] / merged["gdp"]) * 100
    return merged


def _fetch_btc_gold_all() -> pd.DataFrame:
    key = os.getenv("COINGECKO_API_KEY")
    headers = {"x-cg-demo-api-key": key} if key else {}
    with httpx.Client(timeout=30) as client:
        r = client.get(
            "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart",
            params={"vs_currency": "usd", "days": "max"},
            headers=headers,
        )
        r.raise_for_status()
    mcap_data = r.json().get("market_caps", [])
    btc_df = pd.DataFrame(mcap_data, columns=["ts", "btc_mcap"])
    btc_df["date"] = pd.to_datetime(btc_df["ts"], unit="ms").dt.normalize()
    btc = btc_df.groupby("date")["btc_mcap"].last()

    hist = yf.Ticker("GC=F").history(period="max", interval="1d").dropna(subset=["Close"])
    gold_prices = hist["Close"].copy()
    if hasattr(gold_prices.index, "tz") and gold_prices.index.tz is not None:
        gold_prices.index = gold_prices.index.tz_convert(None)
    gold_prices.index = pd.DatetimeIndex(gold_prices.index).normalize()
    gold_mcap = (gold_prices * GOLD_OZ_OUTSTANDING).rename("gold_mcap")

    merged = pd.concat([btc.rename("btc_mcap"), gold_mcap], axis=1).dropna()
    merged["ratio"] = merged["btc_mcap"] / merged["gold_mcap"]
    return merged


def get_buffett_ratio(period: str = "10y") -> list[dict]:
    try:
        merged = _get_or_fetch("buffett_all", _fetch_buffett_all)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Failed to fetch Buffett ratio data: {exc}")

    sliced = _downsample(_slice(merged, period))
    return [
        {
            "timestamp": idx.date().isoformat(),
            "ratio": round(float(row["ratio"]), 2),
            "wilshire": round(float(row["wilshire"]), 2),
            "gdp": round(float(row["gdp"]), 2),
        }
        for idx, row in sliced.iterrows()
    ]


def get_btc_gold_ratio(period: str = "1y") -> list[dict]:
    try:
        merged = _get_or_fetch("btc_gold_all", _fetch_btc_gold_all)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Failed to fetch BTC/Gold ratio data: {exc}")

    sliced = _downsample(_slice(merged, period))
    return [
        {
            "timestamp": str(idx)[:10],
            "ratio": round(float(row["ratio"]), 6),
            "btc_mcap": round(float(row["btc_mcap"]), 0),
            "gold_mcap": round(float(row["gold_mcap"]), 0),
        }
        for idx, row in sliced.iterrows()
    ]
