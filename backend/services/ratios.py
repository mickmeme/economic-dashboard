import time
import threading

import pandas as pd
import yfinance as yf
from fastapi import HTTPException

GOLD_OZ_OUTSTANDING = 6_836_000_000  # estimated total above-ground gold (troy oz)
CACHE_TTL = 3600  # 1 hour

MAX_CHART_POINTS = 500

PERIOD_DAYS = {
    "1y":  365,
    "3y":  365 * 3,
    "5y":  365 * 5,
    "10y": 365 * 10,
    "max": None,
}

# US nominal GDP (billions USD) — annual mid-year estimates.
# Used to interpolate a daily GDP series without an external API dependency.
# Update the final entry each year.
_GDP_ANNUAL = {
    1980: 2_857,  1985: 4_339,  1990: 5_979,  1995: 7_664,
    2000: 10_252, 2001: 10_582, 2002: 10_936, 2003: 11_458,
    2004: 12_214, 2005: 13_037, 2006: 13_815, 2007: 14_452,
    2008: 14_713, 2009: 14_449, 2010: 14_992, 2011: 15_543,
    2012: 16_197, 2013: 16_785, 2014: 17_527, 2015: 18_238,
    2016: 18_745, 2017: 19_543, 2018: 20_612, 2019: 21_433,
    2020: 21_060, 2021: 23_315, 2022: 25_462, 2023: 27_360,
    2024: 29_017, 2025: 29_700,
}

# Approximate BTC circulating supply by year (mid-year estimate, in BTC)
_BTC_SUPPLY = {
    2010: 4_000_000,  2011: 7_500_000,  2012: 9_500_000,
    2013: 11_000_000, 2014: 12_500_000, 2015: 14_000_000,
    2016: 15_500_000, 2017: 16_500_000, 2018: 17_100_000,
    2019: 17_700_000, 2020: 18_200_000, 2021: 18_700_000,
    2022: 19_100_000, 2023: 19_400_000, 2024: 19_687_500,
    2025: 19_800_000,
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


def _normalise_index(s: pd.Series) -> pd.Series:
    """Strip timezone and normalise to midnight."""
    idx = s.index
    if hasattr(idx, "tz") and idx.tz is not None:
        idx = idx.tz_convert(None)
    s.index = pd.DatetimeIndex(idx).normalize()
    return s


def _gdp_daily_series(start: pd.Timestamp, end: pd.Timestamp) -> pd.Series:
    """Build a daily GDP series by linearly interpolating the annual table."""
    years = sorted(_GDP_ANNUAL)
    annual = pd.Series(
        {pd.Timestamp(f"{y}-07-01"): v for y, v in _GDP_ANNUAL.items()}
    )
    daily_index = pd.date_range(start=annual.index.min(), end=end, freq="D")
    gdp = annual.reindex(daily_index).interpolate(method="time").ffill().bfill()
    return gdp[gdp.index >= start]


def _downsample(df: pd.DataFrame) -> pd.DataFrame:
    if len(df) <= MAX_CHART_POINTS:
        return df
    step = max(1, len(df) // MAX_CHART_POINTS)
    sampled = df.iloc[::step].copy()
    if sampled.index[-1] != df.index[-1]:
        sampled = pd.concat([sampled, df.iloc[[-1]]])
    return sampled


def _slice_period(df: pd.DataFrame, period: str) -> pd.DataFrame:
    days = PERIOD_DAYS.get(period)
    if days is None:
        return df
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=days)
    return df[df.index >= cutoff]


def _fetch_buffett_all() -> pd.DataFrame:
    hist = yf.Ticker("^W5000").history(period="max", interval="1d").dropna(subset=["Close"])
    wilshire = _normalise_index(hist["Close"].rename("wilshire"))

    gdp = _gdp_daily_series(wilshire.index.min(), wilshire.index.max())
    merged = wilshire.to_frame()
    merged["gdp"] = gdp.reindex(merged.index).ffill()
    merged = merged.dropna()
    merged["ratio"] = (merged["wilshire"] / merged["gdp"]) * 100
    return merged


def _fetch_btc_gold_all() -> pd.DataFrame:
    btc_hist = yf.Ticker("BTC-USD").history(period="max", interval="1d").dropna(subset=["Close"])
    gold_hist = yf.Ticker("GC=F").history(period="max", interval="1d").dropna(subset=["Close"])

    btc_prices  = _normalise_index(btc_hist["Close"].copy())
    gold_prices = _normalise_index(gold_hist["Close"].copy())

    merged = pd.concat(
        [btc_prices.rename("btc_price"), gold_prices.rename("gold_price")], axis=1
    ).dropna()

    merged["btc_supply"] = merged.index.map(lambda d: _BTC_SUPPLY.get(d.year, 19_800_000))
    merged["btc_mcap"]   = merged["btc_price"]  * merged["btc_supply"]
    merged["gold_mcap"]  = merged["gold_price"] * GOLD_OZ_OUTSTANDING
    merged["ratio"]      = merged["btc_mcap"] / merged["gold_mcap"]
    return merged


def get_buffett_ratio(period: str = "10y") -> list[dict]:
    try:
        merged = _get_or_fetch("buffett_all", _fetch_buffett_all)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Buffett ratio unavailable: {exc}")

    sliced = _downsample(_slice_period(merged, period))
    return [
        {
            "timestamp": idx.date().isoformat(),
            "ratio":    round(float(row["ratio"]),    2),
            "wilshire": round(float(row["wilshire"]), 2),
            "gdp":      round(float(row["gdp"]),      2),
        }
        for idx, row in sliced.iterrows()
    ]


def get_btc_gold_ratio(period: str = "1y") -> list[dict]:
    try:
        merged = _get_or_fetch("btc_gold_all", _fetch_btc_gold_all)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"BTC/Gold ratio unavailable: {exc}")

    sliced = _downsample(_slice_period(merged, period))
    return [
        {
            "timestamp": str(idx)[:10],
            "ratio":    round(float(row["ratio"]),    6),
            "btc_mcap": round(float(row["btc_mcap"]), 0),
            "gold_mcap": round(float(row["gold_mcap"]), 0),
        }
        for idx, row in sliced.iterrows()
    ]
