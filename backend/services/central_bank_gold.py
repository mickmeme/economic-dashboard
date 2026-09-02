import time
import threading
from datetime import datetime

import httpx

TROY_OZ_PER_TONNE = 32_150.7466

# Major central bank gold holders (IMF area codes)
IMF_COUNTRIES = [
    "US", "DE", "IT", "FR", "RU", "CN", "CH", "JP", "IN",
    "NL", "TR", "PL", "AU", "GB", "PT", "SA", "KZ", "UZ",
    "BE", "SG", "SE", "AT", "KR", "GR", "IQ", "TH", "MX",
]

PERIOD_YEARS = {
    "1y":  1,
    "3y":  3,
    "5y":  5,
    "10y": 10,
    "max": None,
}

_cache: dict = {}
_lock = threading.Lock()
CACHE_TTL = 6 * 60 * 60  # 6 hours


def _fetch_raw() -> dict[str, float]:
    """Fetch monthly gold reserves from IMF IFS, return {YYYY-MM: total_tonnes}."""
    countries = "+".join(IMF_COUNTRIES)
    url = (
        "https://dataservices.imf.org/REST/IMF.ashx/CompactData/"
        f"IFS/M.{countries}.1L_BGOLD?startPeriod=2000-01"
    )
    resp = httpx.get(url, timeout=45)
    resp.raise_for_status()
    data = resp.json()

    series_raw = (
        data.get("CompactData", {})
            .get("DataSet", {})
            .get("Series", [])
    )
    if isinstance(series_raw, dict):
        series_raw = [series_raw]

    totals: dict[str, float] = {}

    for series in series_raw:
        unit_mult = int(series.get("@UNIT_MULT", 0))
        multiplier = 10 ** unit_mult  # UNIT_MULT=6 → ×1,000,000 troy oz

        obs = series.get("Obs", [])
        if isinstance(obs, dict):
            obs = [obs]

        for o in obs:
            period = o.get("@TIME_PERIOD")
            val_str = o.get("@OBS_VALUE")
            if not period or not val_str:
                continue
            try:
                troy_oz = float(val_str) * multiplier
                tonnes = troy_oz / TROY_OZ_PER_TONNE
                totals[period] = totals.get(period, 0.0) + tonnes
            except (ValueError, ZeroDivisionError):
                continue

    return totals


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

    sorted_periods = sorted(raw.keys())

    years = PERIOD_YEARS.get(period)
    if years is not None:
        now = datetime.utcnow()
        cutoff_year = now.year - years
        cutoff = f"{cutoff_year}-{now.month:02d}"
        sorted_periods = [p for p in sorted_periods if p >= cutoff]

    result = []
    for i, p in enumerate(sorted_periods):
        total = raw[p]
        net = 0.0 if i == 0 else total - raw.get(sorted_periods[i - 1], total)
        result.append({
            "time": p,
            "total_reserves": round(total, 1),
            "net_purchases": round(net, 2),
        })

    return result
