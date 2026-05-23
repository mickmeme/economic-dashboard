import json
import time
import threading
import urllib.request
import urllib.error
import urllib.parse

# Search for games sorted by release date — category1=998 filters to games only
STEAM_SEARCH_URL = (
    "https://store.steampowered.com/search/results/"
    "?sort_by=Released_DESC&category1=998&json=1&count=20"
)
CACHE_TTL = 1800  # 30 min

_cache: dict = {}
_lock = threading.Lock()


def _capsule_url(app_id: int) -> str:
    return f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app_id}/capsule_616x353.jpg"


def _header_url(app_id: int) -> str:
    return f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app_id}/header.jpg"


def get_new_releases(limit: int = 20) -> list[dict]:
    with _lock:
        if "releases" in _cache:
            fetched_at, data = _cache["releases"]
            if time.time() - fetched_at < CACHE_TTL:
                return data

    req = urllib.request.Request(
        STEAM_SEARCH_URL,
        headers={
            "User-Agent":      "Mozilla/5.0 (compatible; economic-dashboard/1.0)",
            "Accept":          "application/json",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    items = payload.get("items", [])

    results = []
    for item in items:
        if not isinstance(item, dict):
            continue
        app_id = item.get("id")
        if not app_id:
            continue

        price_info   = item.get("price") or {}
        final        = price_info.get("final", 0)
        initial      = price_info.get("initial", 0)
        discount     = price_info.get("discount_percent", 0)
        final_fmt    = price_info.get("final_formatted", "")
        initial_fmt  = price_info.get("initial_formatted", "")

        if final == 0 and initial == 0:
            price_str = "Free"
        elif final_fmt:
            price_str = final_fmt
        else:
            price_str = f"${final / 100:.2f}"

        orig_str = initial_fmt if (discount > 0 and initial_fmt) else None

        # tiny_image from search results; also provide constructed fallbacks
        tiny = item.get("tiny_image") or item.get("image") or ""

        results.append({
            "app_id":         app_id,
            "name":           item.get("name", ""),
            "image_url":      _capsule_url(app_id),
            "header_image":   _header_url(app_id),
            "tiny_image":     tiny,
            "price":          price_str,
            "original_price": orig_str,
            "discount":       discount,
            "store_url":      f"https://store.steampowered.com/app/{app_id}/",
            "release":        item.get("release_string", ""),
        })
        if len(results) >= limit:
            break

    with _lock:
        _cache["releases"] = (time.time(), results)

    return results
