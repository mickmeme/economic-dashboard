import math
import time
import threading

import pandas as pd
import yfinance as yf

# Cache TTLs by period (seconds)
CACHE_TTL = {
    "1d": 5 * 60,
    "1w": 15 * 60,
    "1m": 60 * 60,
    "3m": 60 * 60,
    "1y": 2 * 60 * 60,
    "5y": 6 * 60 * 60,
}

# yfinance period + interval for each UI period
PERIOD_CONFIG = {
    "1d": {"period": "1d",  "interval": "5m"},
    "1w": {"period": "5d",  "interval": "1h"},
    "1m": {"period": "1mo", "interval": "1d"},
    "3m": {"period": "3mo", "interval": "1d"},
    "1y": {"period": "1y",  "interval": "1d"},
    "5y": {"period": "5y",  "interval": "1wk"},
}

RESOURCES = [
    {
        "key": "oil",
        "name": "WTI Crude Oil",
        "ticker": "CL=F",
        "unit": "USD / barrel",
        "color": "#f97316",
        "supply": {
            "pct_mined": 44.7,
            "pct_remaining": 55.3,
            "mined_label": "≈ 1.4 trillion barrels consumed since 1859",
            "remaining_label": "≈ 1.73 trillion barrels in proven reserves",
            "source": "BP Statistical Review of World Energy 2023",
        },
    },
    {
        "key": "gold",
        "name": "Gold",
        "ticker": "GC=F",
        "unit": "USD / troy oz",
        "color": "#FFF97F",
        "supply": {
            "pct_mined": 78.6,
            "pct_remaining": 21.4,
            "mined_label": "≈ 208,874 tonnes ever mined",
            "remaining_label": "≈ 57,000 tonnes in proven reserves",
            "source": "World Gold Council / USGS 2023",
        },
    },
    {
        "key": "silver",
        "name": "Silver",
        "ticker": "SI=F",
        "unit": "USD / troy oz",
        "color": "#9ca3af",
        "supply": {
            "pct_mined": 75.6,
            "pct_remaining": 24.4,
            "mined_label": "≈ 1.74 million tonnes ever mined",
            "remaining_label": "≈ 561,000 tonnes in proven reserves",
            "source": "Silver Institute / USGS 2023",
        },
    },
    {
        "key": "gas",
        "name": "Natural Gas",
        "ticker": "NG=F",
        "unit": "USD / MMBtu",
        "color": "#22c55e",
        "supply": {
            "pct_mined": 42.7,
            "pct_remaining": 57.3,
            "mined_label": "≈ 140 trillion m³ consumed",
            "remaining_label": "≈ 188 trillion m³ in proven reserves",
            "source": "BP Statistical Review of World Energy 2023",
        },
    },
    {
        "key": "coal",
        "name": "Coal",
        "ticker": "BTU",
        "unit": "USD / share — Peabody Energy (coal sector proxy)",
        "color": "#a8a29e",
        "supply": {
            "pct_mined": 44.2,
            "pct_remaining": 55.8,
            "mined_label": "≈ 850 billion tonnes consumed historically",
            "remaining_label": "≈ 1.07 trillion tonnes in proven reserves",
            "source": "BP Statistical Review of World Energy 2023",
        },
    },
    {
        "key": "platinum",
        "name": "Platinum",
        "ticker": "PL=F",
        "unit": "USD / troy oz",
        "color": "#94a3b8",
        "supply": {
            "pct_mined": 12.7,
            "pct_remaining": 87.3,
            "mined_label": "≈ 10,000 tonnes ever mined",
            "remaining_label": "≈ 69,000 tonnes in proven reserves",
            "source": "USGS Mineral Commodity Summaries 2023",
        },
    },
    {
        "key": "palladium",
        "name": "Palladium",
        "ticker": "PA=F",
        "unit": "USD / troy oz",
        "color": "#c084fc",
        "supply": {
            "pct_mined": 9.8,
            "pct_remaining": 90.2,
            "mined_label": "≈ 6,500 tonnes ever mined",
            "remaining_label": "≈ 60,000 tonnes in proven reserves",
            "source": "USGS Mineral Commodity Summaries 2023",
        },
    },
]

RESOURCE_MAP = {r["key"]: r for r in RESOURCES}
VALID_KEYS = set(RESOURCE_MAP)

_cache: dict = {}
_locks: dict = {}
_locks_mutex = threading.Lock()


def _get_lock(key: str) -> threading.Lock:
    with _locks_mutex:
        if key not in _locks:
            _locks[key] = threading.Lock()
    return _locks[key]


def _safe_float(v) -> float | None:
    """Return float or None — guards against NaN/Inf which break JSON serialization."""
    if v is None:
        return None
    try:
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return None


def _normalise_index(hist: pd.DataFrame) -> pd.DataFrame:
    if hasattr(hist.index, "tz") and hist.index.tz is not None:
        hist.index = hist.index.tz_convert(None)
    return hist


def get_resources_list() -> list[dict]:
    result = []
    for r in RESOURCES:
        try:
            info  = yf.Ticker(r["ticker"]).fast_info
            price = _safe_float(getattr(info, "last_price", None))
            prev  = _safe_float(getattr(info, "previous_close", None))
            change_pct = (
                round((price - prev) / prev * 100, 2)
                if price is not None and prev and prev > 0 else None
            )
            result.append({
                "key":        r["key"],
                "name":       r["name"],
                "ticker":     r["ticker"],
                "unit":       r["unit"],
                "color":      r["color"],
                "price":      round(price, 3) if price is not None else None,
                "change_pct": change_pct,
                "supply":     r["supply"],
            })
        except Exception as exc:
            result.append({
                "key":        r["key"],
                "name":       r["name"],
                "ticker":     r["ticker"],
                "unit":       r["unit"],
                "color":      r["color"],
                "price":      None,
                "change_pct": None,
                "supply":     r["supply"],
                "error":      str(exc),
            })
    return result


def get_resource_history(key: str, period: str) -> list[dict]:
    resource = RESOURCE_MAP[key]
    config   = PERIOD_CONFIG[period]
    cache_key = f"rh_{key}_{period}"
    ttl = CACHE_TTL[period]

    with _get_lock(cache_key):
        if cache_key in _cache:
            fetched_at, data = _cache[cache_key]
            if time.time() - fetched_at < ttl:
                return data

        hist = yf.Ticker(resource["ticker"]).history(
            period=config["period"], interval=config["interval"]
        ).dropna(subset=["Close"])
        hist = _normalise_index(hist)

        intraday = period == "1d"
        data = [
            {
                "time":  idx.isoformat() if intraday else str(idx)[:10],
                "value": round(float(row["Close"]), 4),
            }
            for idx, row in hist.iterrows()
        ]

        _cache[cache_key] = (time.time(), data)
        return data
