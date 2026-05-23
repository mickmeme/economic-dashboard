import os
import re
import time
import threading
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

import httpx

NEWSDATA_KEY = os.getenv("NEWSDATA_KEY", "")
NEWSAPI_KEY  = os.getenv("NEWSAPI_KEY", "")

VALID_CATEGORIES = {"global", "gaming", "markets", "3dprinting"}

CACHE_TTL   = 1800  # 30 min
FAILURE_TTL = 120   # 2 min before retrying a failed category

_FAILURE = object()
_cache: dict[str, tuple[float, object]] = {}
_locks: dict[str, threading.Lock] = {}
_locks_mutex = threading.Lock()

_NEWSDATA_CFG = {
    "global":     {"category": "world"},
    "markets":    {"category": "business"},
    "3dprinting": {"q": "3D printer OR 3D printing OR 3D printed"},
}

_NEWSAPI_CFG = {
    "global":     {"_ep": "top-headlines", "category": "general"},
    "markets":    {"_ep": "top-headlines", "category": "business"},
    "3dprinting": {"_ep": "everything",    "q": "3D printer OR 3D printing OR 3D printed", "sortBy": "publishedAt"},
}

_GAMING_RSS_URL = (
    "https://news.google.com/rss/search"
    "?q=game+announcement+OR+game+reveal+OR+game+trailer+OR+new+game+announced"
    "&hl=en-US&gl=US&ceid=US:en"
)

_GAMING_KEYWORDS = {
    "announced", "announce", "announcement", "reveal", "revealed",
    "trailer", "release date", "launches", "launch", "coming soon",
    "teaser", "confirmed", "new game", "gameplay reveal", "debut",
}


def _get_cached(key: str, fn):
    with _locks_mutex:
        if key not in _locks:
            _locks[key] = threading.Lock()
    with _locks[key]:
        if key in _cache:
            fetched_at, data = _cache[key]
            ttl = FAILURE_TTL if data is _FAILURE else CACHE_TTL
            if time.time() - fetched_at < ttl:
                if data is _FAILURE:
                    raise RuntimeError(f"Cached news failure: {key}")
                return data
        try:
            data = fn()
            _cache[key] = (time.time(), data)
            return data
        except Exception:
            _cache[key] = (time.time(), _FAILURE)
            raise


def _fetch_og_image(url: str) -> str:
    """Follow redirects to the article page and scrape og:image / twitter:image."""
    try:
        resp = httpx.get(
            url,
            follow_redirects=True,
            timeout=httpx.Timeout(connect=4.0, read=6.0, write=4.0, pool=4.0),
            headers={"User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )},
        )
        if not resp.is_success:
            return ""
        html = resp.text[:40000]  # og:image is always in <head>
        for pattern in [
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
            r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image["\']',
        ]:
            m = re.search(pattern, html, re.IGNORECASE)
            if m:
                img = m.group(1).strip()
                if img.startswith("http"):
                    return img
        return ""
    except Exception:
        return ""


def _fetch_gaming_rss() -> list[dict]:
    """Fetch Google News RSS for gaming announcements and enrich with og:image."""
    resp = httpx.get(
        _GAMING_RSS_URL,
        follow_redirects=True,
        timeout=httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=5.0),
        headers={"User-Agent": "Mozilla/5.0"},
    )
    if not resp.is_success:
        raise ValueError(f"Google News RSS {resp.status_code}: {resp.text[:300]}")

    root = ET.fromstring(resp.content)
    channel = root.find("channel")
    items = channel.findall("item") if channel is not None else []

    articles = []
    for item in items:
        title  = (item.findtext("title")   or "").strip()
        link   = (item.findtext("link")    or "").strip()
        pub    = (item.findtext("pubDate") or "").strip()
        src_el = item.find("source")
        source = src_el.text.strip() if src_el is not None and src_el.text else ""
        if title and link:
            articles.append({
                "title":        title,
                "description":  "",
                "url":          link,
                "image_url":    "",
                "published_at": pub,
                "source":       source,
            })

    # Fetch og:image for all articles in parallel
    def enrich(article):
        article["image_url"] = _fetch_og_image(article["url"])
        return article

    with ThreadPoolExecutor(max_workers=10) as pool:
        enriched = list(pool.map(enrich, articles))

    return enriched


def _fetch_newsdata(category: str) -> list[dict]:
    cfg = dict(_NEWSDATA_CFG[category])
    params = {"apikey": NEWSDATA_KEY, "language": "en", "size": 10, **cfg}
    resp = httpx.get("https://newsdata.io/api/1/news", params=params,
                     timeout=httpx.Timeout(connect=5.0, read=20.0, write=5.0, pool=5.0),
                     headers={"User-Agent": "Mozilla/5.0"})
    if not resp.is_success:
        raise ValueError(f"NewsData {resp.status_code}: {resp.text[:300]}")
    return [
        {
            "title":        a.get("title") or "",
            "description":  a.get("description") or "",
            "url":          a.get("link") or "",
            "image_url":    a.get("image_url") or "",
            "published_at": a.get("pubDate") or "",
            "source":       a.get("source_name") or a.get("source_id") or "",
        }
        for a in resp.json().get("results", [])
        if (a.get("title") or "").strip() and (a.get("image_url") or "").strip()
    ]


def _fetch_newsapi(category: str) -> list[dict]:
    cfg = dict(_NEWSAPI_CFG[category])
    endpoint = cfg.pop("_ep", "everything")
    params = {"apiKey": NEWSAPI_KEY, "language": "en", "pageSize": 10, **cfg}
    url = f"https://newsapi.org/v2/{endpoint}"
    resp = httpx.get(url, params=params,
                     timeout=httpx.Timeout(connect=5.0, read=20.0, write=5.0, pool=5.0),
                     headers={"User-Agent": "Mozilla/5.0"})
    if not resp.is_success:
        raise ValueError(f"NewsAPI {resp.status_code}: {resp.text[:300]}")
    return [
        {
            "title":        a.get("title") or "",
            "description":  a.get("description") or "",
            "url":          a.get("url") or "",
            "image_url":    a.get("urlToImage") or "",
            "published_at": a.get("publishedAt") or "",
            "source":       (a.get("source") or {}).get("name") or "",
        }
        for a in resp.json().get("articles", [])
        if (a.get("title") or "").strip() not in ("", "[Removed]")
        and (a.get("urlToImage") or "").strip()
    ]


def get_news(category: str) -> list[dict]:
    if category not in VALID_CATEGORIES:
        raise ValueError(f"Unknown news category: {category}")

    def fetch():
        if category == "gaming":
            articles = _fetch_gaming_rss()
            articles = [a for a in articles if any(kw in (a["title"] + " " + a["description"]).lower() for kw in _GAMING_KEYWORDS)]
        elif NEWSDATA_KEY:
            articles = _fetch_newsdata(category)
        elif NEWSAPI_KEY:
            articles = _fetch_newsapi(category)
        else:
            raise ValueError("No news API key set — add NEWSDATA_KEY or NEWSAPI_KEY to environment")

        seen = set()
        deduped = []
        for a in articles:
            raw = a["url"] or a["title"]
            key = raw.strip().lower().rstrip("/").split("?")[0]
            if key and key not in seen:
                seen.add(key)
                deduped.append(a)
        return deduped

    return _get_cached(f"news_{category}", fetch)
