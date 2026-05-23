import csv
import io
import math
import os
import time
import threading
import urllib.request
import urllib.error

import httpx

DOMAIN_CLIENT_ID     = os.getenv("DOMAIN_CLIENT_ID", "")
DOMAIN_CLIENT_SECRET = os.getenv("DOMAIN_CLIENT_SECRET", "")
DOMAIN_TOKEN_URL     = "https://auth.domain.com.au/v1/connect/token"
DOMAIN_API_BASE      = "https://api.domain.com.au"

SALES_CACHE_TTL = 3600  # 1 hour

_token_store: dict = {}
_token_lock  = threading.Lock()
_sales_cache: dict = {}
_sales_lock  = threading.Lock()


def _get_domain_token() -> str:
    with _token_lock:
        if "tok" in _token_store and time.time() < _token_store["expires"] - 60:
            return _token_store["tok"]
        resp = httpx.post(
            DOMAIN_TOKEN_URL,
            data={
                "client_id":     DOMAIN_CLIENT_ID,
                "client_secret": DOMAIN_CLIENT_SECRET,
                "grant_type":    "client_credentials",
                "scope":         "api_listings_read",
            },
            timeout=10,
        )
        if not resp.is_success:
            raise RuntimeError(f"Domain auth failed {resp.status_code}: {resp.text[:200]}")
        d = resp.json()
        _token_store["tok"]     = d["access_token"]
        _token_store["expires"] = time.time() + d.get("expires_in", 3600)
        return _token_store["tok"]


def _parse_sale(item: dict) -> dict:
    """Normalise a Domain API sold listing item."""
    listing = item.get("listing") or item
    pd  = listing.get("propertyDetails") or {}
    pr  = listing.get("priceDetails")    or {}
    ds  = listing.get("dateSold")        or {}
    media = listing.get("media")         or []

    price_val = pr.get("price")
    price_str = pr.get("displayPrice") or ("Price withheld" if not price_val else None)

    date_raw = ds.get("date") or ds.get("matchedDate") or ""
    date_str = date_raw[:10] if date_raw else ""   # keep YYYY-MM-DD

    image_url = next(
        (m["url"] for m in media if isinstance(m, dict) and m.get("category") == "Image"),
        "",
    )

    return {
        "address":       pd.get("displayableAddress") or "",
        "suburb":        (pd.get("suburb") or "").title(),
        "postcode":      pd.get("postcode") or "",
        "property_type": (pd.get("propertyType") or "").title(),
        "bedrooms":      pd.get("bedrooms"),
        "bathrooms":     pd.get("bathrooms"),
        "carspaces":     pd.get("carspaces"),
        "price":         price_val,
        "display_price": price_str or (f"${price_val:,.0f}" if price_val else "Price withheld"),
        "date_sold":     date_str,
        "image_url":     image_url,
    }


def get_recent_sales(postcode: str, limit: int = 10) -> list[dict]:
    with _sales_lock:
        key = f"sales_{postcode}"
        if key in _sales_cache:
            fetched_at, data = _sales_cache[key]
            if time.time() - fetched_at < SALES_CACHE_TTL:
                return data

    token = _get_domain_token()
    resp = httpx.post(
        f"{DOMAIN_API_BASE}/v1/listings/sold",
        json={
            "locations": [{"postCode": postcode}],
            "pageSize":  limit,
            "sort":      {"sortKey": "dateSold", "direction": "Descending"},
        },
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        timeout=15,
    )
    if not resp.is_success:
        raise RuntimeError(f"Domain API {resp.status_code}: {resp.text[:300]}")

    items = resp.json()
    if isinstance(items, dict):
        items = items.get("listings") or items.get("results") or []

    results = [_parse_sale(i) for i in items if isinstance(i, dict)]

    with _sales_lock:
        _sales_cache[key] = (time.time(), results)

    return results

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
