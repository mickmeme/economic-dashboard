import os
import time
import threading
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from typing import Optional

import httpx

CACHE_TTL = 24 * 3600  # 24 hours

DOMAIN_TOKEN_URL = "https://auth.domain.com.au/v1/connect/token"
DOMAIN_SEARCH_URL = "https://api.domain.com.au/v1/listings/residential/_search"

STATES = [
    {"key": "NSW", "label": "New South Wales"},
    {"key": "VIC", "label": "Victoria"},
    {"key": "QLD", "label": "Queensland"},
    {"key": "WA",  "label": "Western Australia"},
    {"key": "SA",  "label": "South Australia"},
    {"key": "TAS", "label": "Tasmania"},
    {"key": "ACT", "label": "ACT"},
    {"key": "NT",  "label": "Northern Territory"},
]

PROPERTY_CONFIGS = {
    "unit": {
        "label": "Unit / Apartment",
        "sublabel": "",
        "property_types": ["ApartmentUnitFlat"],
        "min_beds": None, "max_beds": None, "min_baths": None,
    },
    "townhouse": {
        "label": "Townhouse",
        "sublabel": "",
        "property_types": ["Townhouse"],
        "min_beds": None, "max_beds": None, "min_baths": None,
    },
    "house_small": {
        "label": "Small House",
        "sublabel": "< 3 bedrooms",
        "property_types": ["House"],
        "min_beds": None, "max_beds": 2, "min_baths": None,
    },
    "house_large": {
        "label": "Large House",
        "sublabel": "> 3 bedrooms",
        "property_types": ["House"],
        "min_beds": 4, "max_beds": None, "min_baths": None,
    },
    "house_very_large": {
        "label": "Very Large House",
        "sublabel": "5 bed / 5 bath",
        "property_types": ["House"],
        "min_beds": 5, "max_beds": None, "min_baths": 5,
    },
}

SUBURBS_CONFIG = {
    "point_cook": {
        "label": "Point Cook",
        "state": "VIC",
        "postcode": "3030",
    },
    "varsity_lakes": {
        "label": "Varsity Lakes",
        "state": "QLD",
        "postcode": "4227",
    },
}

_cache: dict = {}
_cache_locks: dict = {}
_cache_locks_mutex = threading.Lock()
_token_lock = threading.Lock()
_token_info: dict = {}


def _get_token() -> str:
    now = time.time()
    if _token_info.get("token") and now < _token_info.get("expires_at", 0) - 60:
        return _token_info["token"]

    with _token_lock:
        if _token_info.get("token") and now < _token_info.get("expires_at", 0) - 60:
            return _token_info["token"]

        client_id = os.environ.get("DOMAIN_CLIENT_ID", "")
        client_secret = os.environ.get("DOMAIN_CLIENT_SECRET", "")
        if not client_id or not client_secret:
            raise RuntimeError(
                "DOMAIN_CLIENT_ID and DOMAIN_CLIENT_SECRET environment variables are required. "
                "Register at developers.domain.com.au for a free API key."
            )

        with httpx.Client(timeout=15) as client:
            resp = client.post(DOMAIN_TOKEN_URL, data={
                "grant_type": "client_credentials",
                "scope": "api_listings_read",
                "client_id": client_id,
                "client_secret": client_secret,
            })
            resp.raise_for_status()
            data = resp.json()

        _token_info["token"] = data["access_token"]
        _token_info["expires_at"] = now + data.get("expires_in", 3600)
        return _token_info["token"]


def _month_ranges() -> tuple[tuple[str, str], tuple[str, str]]:
    """Return (current_month_range, prior_month_range) as (start, end) ISO date tuples."""
    today = date.today()
    curr_start = today.replace(day=1)
    curr_end = today
    prev_end = curr_start - timedelta(days=1)
    prev_start = prev_end.replace(day=1)
    return (
        (curr_start.isoformat(), curr_end.isoformat()),
        (prev_start.isoformat(), prev_end.isoformat()),
    )


def _search_sold_prices(
    location: dict,
    config: dict,
    date_from: str,
    date_to: str,
) -> list[int]:
    token = _get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    payload: dict = {
        "listingType": "Residential",
        "propertyTypes": config["property_types"],
        "saleMode": "sold",
        "soldDateRange": {"min": date_from, "max": date_to},
        "locations": [location],
        "pageSize": 200,
    }
    if config.get("min_beds"):
        payload["minBedrooms"] = config["min_beds"]
    if config.get("max_beds"):
        payload["maxBedrooms"] = config["max_beds"]
    if config.get("min_baths"):
        payload["minBathrooms"] = config["min_baths"]

    prices: list[int] = []
    with httpx.Client(timeout=30) as client:
        for page in range(1, 6):  # max 5 pages × 200 = 1 000 listings
            payload["pageNumber"] = page
            resp = client.post(DOMAIN_SEARCH_URL, json=payload, headers=headers)
            if resp.status_code in (429, 403):
                break
            if not resp.is_success:
                break
            items = resp.json()
            if not items:
                break
            for item in items:
                sold_price = (
                    item.get("listing", {})
                        .get("soldDetails", {})
                        .get("soldPrice")
                )
                if sold_price and sold_price > 0:
                    prices.append(int(sold_price))
            if len(items) < 200:
                break

    return prices


def _compute_stats(prices: list[int]) -> Optional[dict]:
    if not prices:
        return None
    return {
        "median": int(statistics.median(prices)),
        "min": min(prices),
        "max": max(prices),
        "count": len(prices),
    }


def _compute_change(curr: Optional[dict], prev: Optional[dict]) -> dict:
    if not curr or not prev:
        return {}
    out = {}
    for key in ("median", "min", "max"):
        if prev.get(key) and prev[key] > 0:
            out[key] = round((curr[key] - prev[key]) / prev[key] * 100, 2)
    return out


def _fetch_type_data(location: dict, config: dict) -> dict:
    (date_from_curr, date_to_curr), (date_from_prev, date_to_prev) = _month_ranges()

    curr_prices = _search_sold_prices(location, config, date_from_curr, date_to_curr)
    prev_prices = _search_sold_prices(location, config, date_from_prev, date_to_prev)

    curr = _compute_stats(curr_prices)
    prev = _compute_stats(prev_prices)
    return {
        "current": curr,
        "prior": prev,
        "change": _compute_change(curr, prev),
    }


def _fetch_state_overview() -> dict:
    result = {
        "property_types": {
            k: {"label": v["label"], "sublabel": v.get("sublabel", "")}
            for k, v in PROPERTY_CONFIGS.items()
        },
        "states": {s["key"]: {"key": s["key"], "label": s["label"], "types": {}} for s in STATES},
        "fetched_at": date.today().isoformat(),
    }

    tasks: list[tuple[str, str, dict, dict]] = []
    for state_info in STATES:
        location = {"state": state_info["key"]}
        for prop_key, config in PROPERTY_CONFIGS.items():
            tasks.append((state_info["key"], prop_key, location, config))

    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {
            pool.submit(_fetch_type_data, loc, cfg): (sk, pk)
            for sk, pk, loc, cfg in tasks
        }
        for future in as_completed(futures):
            state_key, prop_key = futures[future]
            try:
                result["states"][state_key]["types"][prop_key] = future.result()
            except Exception as exc:
                result["states"][state_key]["types"][prop_key] = {"error": str(exc)}

    result["states"] = list(result["states"].values())
    return result


def _fetch_suburb_overview() -> list:
    suburb_results = {
        k: {
            "key": k,
            "label": v["label"],
            "postcode": v["postcode"],
            "state": v["state"],
            "types": {},
        }
        for k, v in SUBURBS_CONFIG.items()
    }

    tasks: list[tuple[str, str, dict, dict]] = []
    for suburb_key, suburb_info in SUBURBS_CONFIG.items():
        location = {"postCode": suburb_info["postcode"], "state": suburb_info["state"]}
        for prop_key, config in PROPERTY_CONFIGS.items():
            tasks.append((suburb_key, prop_key, location, config))

    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {
            pool.submit(_fetch_type_data, loc, cfg): (sk, pk)
            for sk, pk, loc, cfg in tasks
        }
        for future in as_completed(futures):
            suburb_key, prop_key = futures[future]
            try:
                suburb_results[suburb_key]["types"][prop_key] = future.result()
            except Exception as exc:
                suburb_results[suburb_key]["types"][prop_key] = {"error": str(exc)}

    return list(suburb_results.values())


def _get_cached(key: str, fn):
    with _cache_locks_mutex:
        if key not in _cache_locks:
            _cache_locks[key] = threading.Lock()
    with _cache_locks[key]:
        if key in _cache:
            fetched_at, data = _cache[key]
            if time.time() - fetched_at < CACHE_TTL:
                return data
        data = fn()
        _cache[key] = (time.time(), data)
        return data


def get_state_overview() -> dict:
    return _get_cached("re_states", _fetch_state_overview)


def get_suburb_overview() -> list:
    return _get_cached("re_suburbs", _fetch_suburb_overview)
