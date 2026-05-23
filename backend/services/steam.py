import json
import time
import threading
import urllib.request
import urllib.error

# Search for games sorted by release date — category1=998 filters to games only
STEAM_SEARCH_URL = (
    "https://store.steampowered.com/search/results/"
    "?sort_by=Released_DESC&category1=998&json=1&count=20"
)
CACHE_TTL = 1800  # 30 min

_cache: dict = {}
_lock = threading.Lock()

_APP_ID_RE = re.compile(r'/apps/(\d+)/')


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
        name = (item.get("name") or "").strip()
        logo = item.get("logo") or ""
        if not name or not logo:
            continue

        # App ID is embedded in the logo URL: /apps/12345/
        m = _APP_ID_RE.search(logo)
        if not m:
            continue
        app_id = int(m.group(1))

        results.append({
            "app_id":    app_id,
            "name":      name,
            "image_url": f"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{app_id}/header.jpg",
            "store_url": f"https://store.steampowered.com/app/{app_id}/",
        })
        if len(results) >= limit:
            break

    with _lock:
        _cache["releases"] = (time.time(), results)

    return results
