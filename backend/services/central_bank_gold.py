"""
CFTC Commitment of Traders — COMEX Gold, Disaggregated Report.
Tracks Swap Dealer (major banks & dealers) long/short positions weekly.
Swap Dealers in COMEX gold include JPMorgan, Goldman Sachs, Citigroup, etc.
"""

import csv
import io
import time
import threading
import zipfile
from datetime import datetime

import httpx

TROY_OZ_PER_CONTRACT = 100       # COMEX gold contract size
TROY_OZ_PER_TONNE    = 32_150.7466

CFTC_BASE   = "https://www.cftc.gov/files/dea/history"
DATA_START_YEAR = 2010           # individual year files exist from 2010

PERIOD_YEARS = {
    "1y":  1,
    "3y":  3,
    "5y":  5,
    "10y": 10,
    "max": None,
}

_cache: dict = {}
_lock = threading.Lock()
CACHE_TTL = 24 * 60 * 60  # weekly data; refresh daily


GOLD_CONTRACT = "GOLD - COMMODITY EXCHANGE INC."   # exact 100oz COMEX contract only


def _parse_zip(content: bytes) -> list[dict]:
    z = zipfile.ZipFile(io.BytesIO(content))
    rows = []
    with z.open(z.namelist()[0]) as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig"))
        for row in reader:
            # Exact match — excludes Micro Gold (10oz) and E-mini Gold
            if row.get("Market_and_Exchange_Names", "").strip() != GOLD_CONTRACT:
                continue
            date_str = (row.get("Report_Date_as_YYYY-MM-DD") or "").strip()
            if not date_str:
                continue
            try:
                mm_long  = int((row.get("M_Money_Positions_Long_All")  or "0").strip())
                mm_short = int((row.get("M_Money_Positions_Short_All") or "0").strip())
                rows.append({"date": date_str, "mm_long": mm_long, "mm_short": mm_short,
                              "mm_net": mm_long - mm_short})
            except (ValueError, TypeError):
                continue
    return rows


def _tonnes(contracts: int) -> float:
    return round(contracts * TROY_OZ_PER_CONTRACT / TROY_OZ_PER_TONNE, 1)


def _fetch_raw() -> list[dict]:
    all_rows: list[dict] = []
    current_year = datetime.utcnow().year

    for year in range(DATA_START_YEAR, current_year + 1):
        url = f"{CFTC_BASE}/com_disagg_txt_{year}.zip"
        try:
            r = httpx.get(url, timeout=60, follow_redirects=True)
            if r.status_code == 200:
                all_rows.extend(_parse_zip(r.content))
        except Exception:
            continue

    # deduplicate + sort
    seen: set = set()
    unique: list[dict] = []
    for row in sorted(all_rows, key=lambda r: r["date"]):
        if row["date"] not in seen:
            seen.add(row["date"])
            unique.append(row)
    return unique


def get_central_bank_gold(period: str, granularity: str = "w") -> list[dict]:
    with _lock:
        cached = _cache.get("__raw__")
        if cached:
            fetched_at, raw = cached
            if time.time() - fetched_at >= CACHE_TTL:
                cached = None
        if not cached:
            raw = _fetch_raw()
            _cache["__raw__"] = (time.time(), raw)

    # Period filter
    years = PERIOD_YEARS.get(period)
    if years is not None:
        cutoff = f"{datetime.utcnow().year - years}-01-01"
        data = [r for r in raw if r["date"] >= cutoff]
    else:
        data = list(raw)

    if not data:
        return []

    if granularity == "m":
        buckets: dict[str, list[int]] = {}
        for row in data:
            key = row["date"][:7]
            buckets.setdefault(key, []).append(row["mm_net"])

        result = []
        prev = None
        for key in sorted(buckets):
            avg_net = round(sum(buckets[key]) / len(buckets[key]))
            net_t = _tonnes(avg_net)
            change_t = 0.0 if prev is None else round(net_t - prev, 1)
            result.append({"time": key, "net_t": net_t, "change_t": change_t})
            prev = net_t
    else:
        result = []
        prev = None
        for row in data:
            net_t = _tonnes(row["mm_net"])
            change_t = 0.0 if prev is None else round(net_t - prev, 1)
            result.append({"time": row["date"], "net_t": net_t, "change_t": change_t})
            prev = net_t

    return result
