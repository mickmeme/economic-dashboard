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

# Direct RSS feeds from dedicated 3D printing news sites
_3DPRINTING_FEEDS = [
    "https://3dprint.com/feed/",
    "https://all3dp.com/feed/",
    "https://3dprintingindustry.com/feed/",
    "https://www.fabbaloo.com/feed",
    "https://hackaday.com/tag/3d-printing/feed/",
    "https://www.3dnatives.com/en/feed/",
]

# Direct RSS feeds from gaming news sites — images are in the feed XML, no scraping needed
_GAMING_FEEDS = [
    "https://feeds.ign.com/ign/all",
    "https://www.gamespot.com/feeds/mashup/",
    "https://www.polygon.com/rss/index.xml",
    "https://www.pcgamer.com/rss/",
    "https://www.eurogamer.net/?format=rss",
    "https://kotaku.com/rss",
    "https://www.gamesradar.com/rss/",
]

_MEDIA_NS = "http://search.yahoo.com/mrss/"

_OG_IMAGE_RE = re.compile(
    r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']'
    r'|<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
    re.IGNORECASE,
)


def _fetch_og_image(url: str) -> str:
    """Fetch og:image from an article page. Returns '' on any failure."""
    try:
        resp = httpx.get(
            url,
            follow_redirects=True,
            timeout=httpx.Timeout(connect=4.0, read=8.0, write=4.0, pool=4.0),
            headers={"User-Agent": "Mozilla/5.0"},
        )
        if not resp.is_success:
            return ""
        m = _OG_IMAGE_RE.search(resp.text[:20_000])
        if m:
            img = (m.group(1) or m.group(2) or "").strip()
            return img if img.startswith("http") else ""
    except Exception:
        pass
    return ""


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


def _parse_rss_image(item) -> str:
    """Extract image URL from an RSS item using multiple strategies."""
    # media:content
    mc = item.find(f"{{{_MEDIA_NS}}}content")
    if mc is not None:
        url = mc.get("url", "")
        if url.startswith("http"):
            return url

    # media:thumbnail
    mt = item.find(f"{{{_MEDIA_NS}}}thumbnail")
    if mt is not None:
        url = mt.get("url", "")
        if url.startswith("http"):
            return url

    # enclosure
    enc = item.find("enclosure")
    if enc is not None:
        url  = enc.get("url", "")
        mime = enc.get("type", "")
        if url.startswith("http") and "image" in mime:
            return url

    # first <img> inside <description> HTML
    desc = item.findtext("description") or ""
    m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', desc, re.IGNORECASE)
    if m:
        url = m.group(1)
        if url.startswith("http"):
            return url

    return ""


def _fetch_single_gaming_feed(feed_url: str) -> list[dict]:
    """Fetch one gaming RSS feed and return normalised articles."""
    try:
        resp = httpx.get(
            feed_url,
            follow_redirects=True,
            timeout=httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=5.0),
            headers={"User-Agent": "Mozilla/5.0"},
        )
        if not resp.is_success:
            return []

        root    = ET.fromstring(resp.content)
        channel = root.find("channel")
        if channel is None:
            return []

        feed_name = (channel.findtext("title") or feed_url.split("/")[2]).strip()
        candidates = []

        for item in channel.findall("item"):
            title = (item.findtext("title")   or "").strip()
            link  = (item.findtext("link")    or
                     item.findtext("guid")    or "").strip()
            pub   = (item.findtext("pubDate") or "").strip()
            src_el = item.find("source")
            source = src_el.text.strip() if src_el is not None and src_el.text else feed_name
            image  = _parse_rss_image(item)

            if title and link:
                candidates.append({
                    "title":        title,
                    "description":  "",
                    "url":          link,
                    "image_url":    image,
                    "published_at": pub,
                    "source":       source,
                })

        # Fetch og:image in parallel for articles that are missing one
        missing = [a for a in candidates if not a["image_url"]]
        if missing:
            with ThreadPoolExecutor(max_workers=min(len(missing), 6)) as pool:
                og_images = list(pool.map(lambda a: _fetch_og_image(a["url"]), missing))
            for article, og in zip(missing, og_images):
                article["image_url"] = og

        return [a for a in candidates if a["image_url"]]
    except Exception:
        return []


def _fetch_gaming_rss() -> list[dict]:
    """Fetch all gaming RSS feeds in parallel and aggregate results."""
    with ThreadPoolExecutor(max_workers=len(_GAMING_FEEDS)) as pool:
        results = list(pool.map(_fetch_single_gaming_feed, _GAMING_FEEDS))
    all_articles = []
    for feed_articles in results:
        all_articles.extend(feed_articles)
    return all_articles


def _fetch_3dprinting_rss() -> list[dict]:
    """Fetch all 3D printing RSS feeds in parallel and aggregate results."""
    with ThreadPoolExecutor(max_workers=len(_3DPRINTING_FEEDS)) as pool:
        results = list(pool.map(_fetch_single_gaming_feed, _3DPRINTING_FEEDS))
    all_articles = []
    for feed_articles in results:
        all_articles.extend(feed_articles)
    return all_articles


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
            articles = [a for a in articles if any(kw in a["title"].lower() for kw in _GAMING_KEYWORDS)]
        elif category == "3dprinting":
            articles = _fetch_3dprinting_rss()
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
