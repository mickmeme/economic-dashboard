import json
import time
import threading
import urllib.request
import urllib.error

STEAM_FEATURED_URL = "https://store.steampowered.com/api/featuredcategories/?l=english&cc=US"
CACHE_TTL = 1800  # 30 min

_cache: dict = {}
_lock = threading.Lock()


def _header_image(app_id: int) -> str:
    return f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app_id}/header.jpg"


def get_new_releases(limit: int = 20) -> list[dict]:
    with _lock:
        if "releases" in _cache:
            fetched_at, data = _cache["releases"]
            if time.time() - fetched_at < CACHE_TTL:
                return data

    req = urllib.request.Request(
        STEAM_FEATURED_URL,
        headers={"User-Agent": "Mozilla/5.0 (compatible; economic-dashboard/1.0)"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    items = payload.get("new_releases", {}).get("items", [])

    results = []
    for item in items:
        if not isinstance(item, dict):
            continue
        app_id = item.get("id")
        if not app_id:
            continue

        original  = item.get("original_price") or item.get("final_price") or 0
        final     = item.get("final_price") or 0
        discount  = item.get("discount_percent") or 0
        currency  = item.get("currency", "USD")
        symbol    = "$"  # USD default

        if final == 0:
            price_str = "Free"
        else:
            price_str = f"{symbol}{final / 100:.2f}"

        orig_str = f"{symbol}{original / 100:.2f}" if discount > 0 else None

        image = (
            item.get("large_capsule_image")
            or item.get("small_capsule_image")
            or _header_image(app_id)
        )

        results.append({
            "app_id":         app_id,
            "name":           item.get("name", ""),
            "image_url":      image,
            "header_image":   _header_image(app_id),
            "price":          price_str,
            "original_price": orig_str,
            "discount":       discount,
            "currency":       currency,
            "store_url":      f"https://store.steampowered.com/app/{app_id}/",
            "win":            item.get("win_available", False),
            "mac":            item.get("mac_available", False),
            "linux":          item.get("linux_available", False),
        })
        if len(results) >= limit:
            break

    with _lock:
        _cache["releases"] = (time.time(), results)

    return results
