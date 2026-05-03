import os
import time
import threading
import httpx
from datetime import datetime, timezone
from fastapi import HTTPException

COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY")

COINS = [
    {"id": "bitcoin",     "symbol": "BTC",  "name": "Bitcoin"},
    {"id": "ethereum",    "symbol": "ETH",  "name": "Ethereum"},
    {"id": "ripple",      "symbol": "XRP",  "name": "XRP"},
    {"id": "hyperliquid", "symbol": "HYPE", "name": "Hyperliquid"},
]

COINGECKO_BASE = "https://api.coingecko.com/api/v3"

DAYS_MAP = {
    "1d": "1",
    "1w": "7",
    "1m": "30",
    "3m": "90",
    "1y": "365",
    # Warmup variants — extended lookback for BB seeding
    "1d_warmup": "1",    # CoinGecko free tier only offers 1 day of 5-min data
    "1w_warmup": "30",   # 30 days at hourly granularity (same as 7d)
    "1m_warmup": "90",
    "3m_warmup": "365",
    "1y_warmup": "365",  # CoinGecko free tier caps at 365 days
}

# In-memory cache: key -> (fetched_at, data)
_cache: dict[str, tuple[float, any]] = {}
# Per-key locks prevent multiple threads from calling CoinGecko simultaneously
_key_locks: dict[str, threading.Lock] = {}
_key_locks_mutex = threading.Lock()
CACHE_TTL = 300  # 5 minutes — well under rate limits and survives page refreshes


def _coingecko_get(path: str, params: dict) -> dict:
    """Fetch from CoinGecko with per-key locking, caching, and graceful 429 handling."""
    cache_key = path + str(sorted(params.items()))

    # Fast path: return cached data without acquiring a lock
    if cache_key in _cache:
        fetched_at, data = _cache[cache_key]
        if time.time() - fetched_at < CACHE_TTL:
            return data

    # Get or create a per-key lock so only one thread fetches per endpoint
    with _key_locks_mutex:
        if cache_key not in _key_locks:
            _key_locks[cache_key] = threading.Lock()
        lock = _key_locks[cache_key]

    with lock:
        # Re-check after acquiring lock — another thread may have populated the cache
        if cache_key in _cache:
            fetched_at, data = _cache[cache_key]
            if time.time() - fetched_at < CACHE_TTL:
                return data

        try:
            headers = {"x-cg-demo-api-key": COINGECKO_API_KEY} if COINGECKO_API_KEY else {}
            with httpx.Client(timeout=30) as client:
                response = client.get(f"{COINGECKO_BASE}{path}", params=params, headers=headers)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                # Return stale cache rather than failing hard
                if cache_key in _cache:
                    return _cache[cache_key][1]
                raise HTTPException(status_code=503, detail="CoinGecko rate limit reached — try again shortly")
            raise HTTPException(status_code=502, detail=f"CoinGecko error: {exc.response.status_code}")

        _cache[cache_key] = (time.time(), data)
        return data


def _get_global() -> dict:
    """Fetch dominance % and total USD market cap from CoinGecko /global."""
    try:
        data = _coingecko_get("/global", {})
        gd = data.get("data", {})
        return {
            "dominance": gd.get("market_cap_percentage", {}),
            "total_market_cap": gd.get("total_market_cap", {}).get("usd"),
        }
    except Exception:
        return {"dominance": {}, "total_market_cap": None}


def get_crypto() -> list[dict]:
    coin_ids = ",".join(c["id"] for c in COINS)
    data = _coingecko_get("/simple/price", {
        "ids": coin_ids,
        "vs_currencies": "usd",
        "include_24hr_change": "true",
        "include_market_cap": "true",
    })
    global_data = _get_global()
    dominance        = global_data["dominance"]
    total_market_cap = global_data["total_market_cap"]

    results = []
    for coin in COINS:
        coin_data  = data.get(coin["id"], {})
        price      = coin_data.get("usd")
        change     = coin_data.get("usd_24h_change")
        market_cap = coin_data.get("usd_market_cap")
        dom        = dominance.get(coin["symbol"].lower())
        results.append({
            "id": coin["id"],
            "symbol": coin["symbol"],
            "name": coin["name"],
            "section": "crypto",
            "currency": "USD",
            "price": price,
            "change_percent": round(change, 2) if change is not None else None,
            "market_cap": market_cap,
            "total_market_cap": total_market_cap,
            "dominance": round(dom, 2) if dom is not None else None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
    return results


def get_crypto_history(coin_id: str, period: str = "1m") -> list[dict]:
    days = DAYS_MAP.get(period, "30")
    data = _coingecko_get(f"/coins/{coin_id}/market_chart", {
        "vs_currency": "usd",
        "days": days,
    })

    volume_by_ts     = {v[0]: v[1] for v in data.get("total_volumes", [])}
    market_cap_by_ts = {m[0]: m[1] for m in data.get("market_caps", [])}

    return [
        {
            "timestamp":  datetime.fromtimestamp(point[0] / 1000, tz=timezone.utc).isoformat(),
            "price":      point[1],
            "volume":     volume_by_ts.get(point[0], 0),
            "market_cap": market_cap_by_ts.get(point[0]),
        }
        for point in data.get("prices", [])
    ]
