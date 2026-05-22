import os
import time
import threading

import httpx

NEWSDATA_KEY = os.getenv("NEWSDATA_KEY", "")
NEWSAPI_KEY  = os.getenv("NEWSAPI_KEY", "")

VALID_CATEGORIES = {"global", "gaming", "markets", "3dprinting"}

CACHE_TTL   = 1800  # 30 min — balances freshness vs free-tier quota
FAILURE_TTL = 120   # 2 min before retrying a failed category

_FAILURE = object()
_cache: dict[str, tuple[float, object]] = {}
_locks: dict[str, threading.Lock] = {}
_locks_mutex = threading.Lock()

_NEWSDATA_CFG = {
    "global":     {"category": "world"},
    "gaming":     {"q": "gaming OR esports OR \"video games\""},
    "markets":    {"category": "business"},
    "3dprinting": {"q": "\"3D printing\" OR \"additive manufacturing\""},
}

_NEWSAPI_CFG = {
    "global":     {"_ep": "top-headlines", "category": "general"},
    "gaming":     {"_ep": "everything",    "q": "gaming OR esports OR \"video games\"",        "sortBy": "publishedAt"},
    "markets":    {"_ep": "top-headlines", "category": "business"},
    "3dprinting": {"_ep": "everything",    "q": "\"3D printing\" OR \"additive manufacturing\"", "sortBy": "publishedAt"},
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


def _fetch_newsdata(category: str) -> list[dict]:
    cfg = dict(_NEWSDATA_CFG[category])
    params = {"apikey": NEWSDATA_KEY, "language": "en", "size": 10, **cfg}
    resp = httpx.get("https://newsdata.io/api/1/news", params=params,
                     timeout=httpx.Timeout(connect=5.0, read=20.0, write=5.0, pool=5.0),
                     headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
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
        if (a.get("title") or "").strip()
    ]


def _fetch_newsapi(category: str) -> list[dict]:
    cfg = dict(_NEWSAPI_CFG[category])
    endpoint = cfg.pop("_ep", "everything")
    params = {"apiKey": NEWSAPI_KEY, "language": "en", "pageSize": 10, **cfg}
    url = f"https://newsapi.org/v2/{endpoint}"
    resp = httpx.get(url, params=params,
                     timeout=httpx.Timeout(connect=5.0, read=20.0, write=5.0, pool=5.0),
                     headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
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
    ]


def get_news(category: str) -> list[dict]:
    if category not in VALID_CATEGORIES:
        raise ValueError(f"Unknown news category: {category}")

    def fetch():
        if NEWSDATA_KEY:
            return _fetch_newsdata(category)
        if NEWSAPI_KEY:
            return _fetch_newsapi(category)
        raise ValueError("No news API key set — add NEWSDATA_KEY or NEWSAPI_KEY to environment")

    return _get_cached(f"news_{category}", fetch)
