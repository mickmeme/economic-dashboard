import json
import time
import threading
import urllib.request
import urllib.error

# featuredcategories returns Steam's curated front-page lists including "New & Trending"
STEAM_FEATURED_URL = "https://store.steampowered.com/api/featuredcategories/"
CACHE_TTL = 1800  # 30 min

_cache: dict = {}
_lock = threading.Lock()


def get_new_releases(limit: int = 20) -> list[dict]:
    with _lock:
        if "releases" in _cache:
            fetched_at, data = _cache["releases"]
            if time.time() - fetched_at < CACHE_TTL:
                return data

    req = urllib.request.Request(
        STEAM_FEATURED_URL,
        headers={
            "User-Agent":      "Mozilla/5.0 (compatible; economic-dashboard/1.0)",
            "Accept":          "application/json",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    # Find the "New & Trending" category — iterate all keys and match by name,
    # falling back to the first numeric key if no name match is found.
    items = []
    fallback_items = []
    for key, val in payload.items():
        if not isinstance(val, dict):
            continue
        cat_name = val.get("name", "")
        cat_items = val.get("items", [])
        if "trend" in cat_name.lower() or ("new" in cat_name.lower() and "trend" in cat_name.lower()):
            items = cat_items
            break
        if key.isdigit() and not fallback_items and cat_items:
            fallback_items = cat_items
    if not items:
        items = fallback_items

    results = []
    for item in items:
        if not isinstance(item, dict):
            continue
        app_id = item.get("id")
        name   = (item.get("name") or "").strip()
        if not app_id or not name:
            continue

        image_url = (
            item.get("header_image")
            or f"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{app_id}/header.jpg"
        )

        results.append({
            "app_id":    app_id,
            "name":      name,
            "image_url": image_url,
            "store_url": f"https://store.steampowered.com/app/{app_id}/",
        })
        if len(results) >= limit:
            break

    with _lock:
        _cache["releases"] = (time.time(), results)

    return results
