import csv
import io
import json
import math
import os
import re
import time
import threading
import urllib.request
import urllib.error

import httpx

SALES_CACHE_TTL = 3600  # 1 hour

_sales_cache: dict = {}
_sales_lock  = threading.Lock()

_POSTCODE_SLUG = {
    "3030": "point-cook-vic-3030",
    "4227": "varsity-lakes-qld-4227",
}

_SCRAPE_HEADERS = {
    "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-AU,en;q=0.9",
    "Cache-Control":   "no-cache",
}


def _find_listings(obj, depth: int = 0) -> list:
    """Recursively search __NEXT_DATA__ for a list that looks like property listings."""
    if depth > 8:
        return []
    if isinstance(obj, dict):
        for key in ("listings", "results", "cards", "items"):
            val = obj.get(key)
            if isinstance(val, list) and val:
                first = val[0]
                if isinstance(first, dict) and any(k in first for k in (
                    "id", "listingId", "address", "suburb", "price", "bedrooms"
                )):
                    return val
        for v in obj.values():
            found = _find_listings(v, depth + 1)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _find_listings(item, depth + 1)
            if found:
                return found
    return []


def _coerce_str(v) -> str:
    return v if isinstance(v, str) else ""


def _parse_scraped_sale(item: dict) -> dict:
    # Unwrap common nesting patterns
    for wrapper in ("listing", "card"):
        if wrapper in item and isinstance(item[wrapper], dict):
            item = item[wrapper]
            break

    # Address
    addr = item.get("address") or {}
    if isinstance(addr, dict):
        street = " ".join(filter(None, [
            _coerce_str(addr.get("streetNumber")),
            _coerce_str(addr.get("streetName")),
            _coerce_str(addr.get("streetType")),
        ]))
        suburb   = _coerce_str(addr.get("suburb")).title()
        state    = _coerce_str(addr.get("state"))
        postcode = _coerce_str(addr.get("postcode"))
        address  = ", ".join(filter(None, [street, f"{suburb} {state} {postcode}".strip()]))
    else:
        address  = _coerce_str(addr or item.get("displayableAddress") or item.get("displayAddress"))
        suburb   = _coerce_str(item.get("suburb")).title()
        state    = _coerce_str(item.get("state"))
        postcode = _coerce_str(item.get("postcode"))

    # Price
    price_raw = item.get("price") or item.get("soldPrice") or item.get("priceDetails") or {}
    if isinstance(price_raw, dict):
        price_val = price_raw.get("price") or price_raw.get("value")
        display_price = price_raw.get("displayPrice") or price_raw.get("label") or ""
    else:
        price_val = price_raw if isinstance(price_raw, (int, float)) else None
        display_price = _coerce_str(item.get("displayPrice") or item.get("priceLabel"))
    if not display_price:
        display_price = f"${price_val:,.0f}" if price_val else "Price withheld"

    # Date
    date_raw = item.get("dateSold") or item.get("soldDate") or item.get("saleDate") or ""
    if isinstance(date_raw, dict):
        date_raw = date_raw.get("date") or date_raw.get("value") or ""
    date_sold = _coerce_str(date_raw)[:10]

    # Image
    media = item.get("media") or item.get("images") or item.get("photos") or []
    image_url = ""
    for m in media:
        if isinstance(m, dict):
            url = m.get("url") or m.get("imageUrl") or m.get("src") or ""
            if _coerce_str(url).startswith("http"):
                image_url = url
                break

    return {
        "address":       address,
        "suburb":        suburb,
        "postcode":      postcode,
        "property_type": _coerce_str(item.get("propertyType") or item.get("type")).title(),
        "bedrooms":      item.get("bedrooms"),
        "bathrooms":     item.get("bathrooms"),
        "carspaces":     item.get("carspaces") or item.get("parking"),
        "price":         price_val,
        "display_price": display_price,
        "date_sold":     date_sold,
        "image_url":     image_url,
    }


def get_recent_sales(postcode: str, limit: int = 10) -> list[dict]:
    with _sales_lock:
        key = f"sales_{postcode}"
        if key in _sales_cache:
            fetched_at, data = _sales_cache[key]
            if time.time() - fetched_at < SALES_CACHE_TTL:
                return data

    slug = _POSTCODE_SLUG.get(postcode)
    if not slug:
        raise RuntimeError(f"No URL mapping for postcode {postcode}")

    url  = f"https://www.domain.com.au/sold-listings/{slug}/"
    resp = httpx.get(url, headers=_SCRAPE_HEADERS, follow_redirects=True, timeout=30)
    if not resp.is_success:
        raise RuntimeError(f"Domain scrape failed {resp.status_code} for {url}")

    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', resp.text, re.DOTALL)
    if not m:
        raise RuntimeError("Domain: __NEXT_DATA__ not found — page structure may have changed")

    page_data = json.loads(m.group(1))
    raw_listings = _find_listings(page_data)
    if not raw_listings:
        raise RuntimeError("Domain: could not locate listings in page data")

    results = [_parse_scraped_sale(i) for i in raw_listings[:limit] if isinstance(i, dict)]

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
