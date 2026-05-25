import json
import time
import threading
import urllib.request
import urllib.error

# featuredcategories exposes Steam's curated store lists.
# The "new_releases" key is the New Releases section shown on the Steam front page.
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

    items = payload.get("new_releases", {}).get("items", [])

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
