import csv
import io
import math
import os
import time
import threading
import urllib.request
import urllib.error

import httpx


def get_recent_sales(postcode: str, limit: int = 10) -> list[dict]:
    return []


ABS_URL = "https://api.data.abs.gov.au/data/ABS,RES_DWELL_ST"

CACHE_TTL = 6 * 3600  # 6 hours (ABS updates quarterly)

REGIONS = [
    {"id": "AUS", "key": "AUS", "label": "National Average"},
    {"id": "1",   "key": "NSW", "label": "New South Wales"},
    {"id": "2",   "key": "VIC", "label": "Victoria"},
    {"id": "3",   "key": "QLD", "label": "Queensland"},
    {"id": "4",   "key": "SA",  "label": "South Australia"},
    {"id": "5",   "key": "WA",  "label": "Western Australia"},
    {"id": "6",   "key": "TAS", "label": "Tasmania"},
    {"id": "7",   "key": "NT",  "label": "Northern Territory"},
    {"id": "8",   "key": "ACT", "label": "ACT"},
]

_cache: dict = {}
_lock = threading.Lock()


def _safe_float(v):
    if v is None:
        return None
    try:
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return None


def _fetch_abs() -> dict:
    """Fetch mean dwelling value (Measure 5, AUD thousands) for all regions from ABS."""
    req = urllib.request.Request(
        ABS_URL,
        headers={
            "Accept": "text/csv",
            "User-Agent": "Mozilla/5.0 (compatible; economic-dashboard/1.0)",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        text = resp.read().decode("utf-8-sig")

    region_series: dict = {}
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        if row.get("MEASURE", "").strip() != "5":
            continue
        region_id = row.get("REGION", "").strip()
        period    = row.get("TIME_PERIOD", "").strip()
        value     = _safe_float(row.get("OBS_VALUE"))
        if value is None or not period:
            continue
        region_series.setdefault(region_id, []).append((period, value))

    for rid in region_series:
        region_series[rid].sort(key=lambda x: x[0])

    return region_series


def _build_states(region_series: dict) -> list:
    states = []
    for info in REGIONS:
        series = region_series.get(info["id"], [])
        if not series:
            continue

        cur_period, cur_val = series[-1]
        cur_price = round(cur_val * 1000)  # AUD thousands → AUD

        qoq_pct = qoq_abs = yoy_pct = None
        if len(series) >= 2:
            _, prev_val = series[-2]
            if prev_val > 0:
                qoq_pct = round((cur_val - prev_val) / prev_val * 100, 2)
                qoq_abs = round((cur_val - prev_val) * 1000)
        if len(series) >= 5:
            _, yoy_val = series[-5]
            if yoy_val > 0:
                yoy_pct = round((cur_val - yoy_val) / yoy_val * 100, 2)

        history = [
            {"quarter": p, "value": round(v * 1000)}
            for p, v in series[-20:]  # last 5 years of quarterly data
        ]

        states.append({
            "key":     info["key"],
            "label":   info["label"],
            "price":   cur_price,
            "period":  cur_period,
            "qoq_pct": qoq_pct,
            "qoq_abs": qoq_abs,
            "yoy_pct": yoy_pct,
            "history": history,
        })
    return states


def _get_data() -> list:
    with _lock:
        if "states" in _cache:
            fetched_at, data = _cache["states"]
            if time.time() - fetched_at < CACHE_TTL:
                return data
        data = _build_states(_fetch_abs())
        _cache["states"] = (time.time(), data)
        return data


def get_state_overview() -> dict:
    states = _get_data()
    period = states[0]["period"] if states else None
    return {"states": states, "period": period, "source": "ABS RES_DWELL_ST"}


def get_suburb_overview() -> list:
    return []
