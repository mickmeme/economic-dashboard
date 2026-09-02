import time
import threading
from datetime import datetime

import httpx

# Top central bank gold holders (World Bank country codes)
WB_COUNTRIES = "US;DE;IT;FR;RU;CN;CH;JP;IN;NL;TR;PL;AU;GB;PT;SA;KZ;BE;SE;AT;KR;TH;MX"

PERIOD_YEARS = {
    "5y":  5,
    "10y": 10,
    "15y": 15,
    "max": None,
}

WB_BASE = "https://api.worldbank.org/v2"

_cache: dict = {}
_lock = threading.Lock()
CACHE_TTL = 6 * 60 * 60  # 6 hours — WB data is annual


def _fetch_wb(indicator: str) -> dict[tuple, float]:
    url = (
        f"{WB_BASE}/country/{WB_COUNTRIES}/indicator/{indicator}"
        "?format=json&per_page=2000&date=2000:2025"
    )
    resp = httpx.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return {
        (entry["country"]["id"], entry["date"]): entry["value"]
        for entry in (data[1] or [])
        if entry.get("value") is not None
    }


def _fetch_raw() -> dict[str, float]:
    """Return {YYYY: gold_reserve_usd} summed across major central banks."""
    total_map = _fetch_wb("FI.RES.TOTL.CD")   # total reserves incl. gold (USD)
    exgld_map = _fetch_wb("FI.RES.XGLD.CD")   # total reserves excl. gold (USD)

    by_year: dict[str, float] = {}
    for (country, year), total in total_map.items():
        exgld = exgld_map.get((country, year))
        if exgld is None:
            continue
        gold_usd = total - exgld
        if gold_usd <= 0:
            continue
        by_year[year] = by_year.get(year, 0.0) + gold_usd

    return by_year


def get_central_bank_gold(period: str) -> list[dict]:
    with _lock:
        cached = _cache.get("__raw__")
        if cached:
            fetched_at, raw = cached
            if time.time() - fetched_at >= CACHE_TTL:
                cached = None
        if not cached:
            raw = _fetch_raw()
            _cache["__raw__"] = (time.time(), raw)

    sorted_years = sorted(raw.keys())

    years = PERIOD_YEARS.get(period)
    if years is not None:
        cutoff = str(datetime.utcnow().year - years)
        sorted_years = [y for y in sorted_years if y >= cutoff]

    result = []
    for i, year in enumerate(sorted_years):
        total_usd = raw[year]
        net_usd = 0.0 if i == 0 else total_usd - raw.get(sorted_years[i - 1], total_usd)
        result.append({
            "time": year,
            "total_bn": round(total_usd / 1e9, 1),   # USD billions
            "net_bn":   round(net_usd  / 1e9, 1),    # change vs prior year
        })

    return result
