import yfinance as yf
from datetime import datetime, timezone

INSTRUMENTS = [
    # Global Indices — all converted to USD at response time
    {"ticker": "^GSPC",      "name": "S&P 500 (USA)",           "section": "global",     "currency": "USD", "native": "USD"},
    {"ticker": "^AXJO",      "name": "ASX 200 (Australia)",      "section": "global",     "currency": "USD", "native": "AUD"},
    {"ticker": "000001.SS",  "name": "Shanghai Composite (China)","section": "global",    "currency": "USD", "native": "CNY"},
    {"ticker": "^NSEI",      "name": "Nifty 50 (India)",         "section": "global",     "currency": "USD", "native": "INR"},
    # Australian Sector ETFs — kept in AUD
    {"ticker": "ATEC.AX",  "name": "Technology",  "section": "au_sectors", "currency": "AUD", "native": "AUD"},
    {"ticker": "MVR.AX",   "name": "Materials",   "section": "au_sectors", "currency": "AUD", "native": "AUD"},
    {"ticker": "WDS.AX",   "name": "Energy",      "section": "au_sectors", "currency": "AUD", "native": "AUD"},
    {"ticker": "QFN.AX",   "name": "Finance",     "section": "au_sectors", "currency": "AUD", "native": "AUD"},
    {"ticker": "OZR.AX",   "name": "Health",      "section": "au_sectors", "currency": "AUD", "native": "AUD"},
    {"ticker": "VAP.AX",   "name": "Real Estate", "section": "au_sectors", "currency": "AUD", "native": "AUD"},
    {"ticker": "ARMR.AX",  "name": "Defence",     "section": "au_sectors", "currency": "AUD", "native": "AUD"},
    {"ticker": "EOS.AX",   "name": "Space",       "section": "au_sectors", "currency": "AUD", "native": "AUD"},
    # US Sector ETFs — USD
    {"ticker": "XLK",   "name": "Technology",  "section": "us_sectors", "currency": "USD", "native": "USD"},
    {"ticker": "XLB",   "name": "Materials",   "section": "us_sectors", "currency": "USD", "native": "USD"},
    {"ticker": "XLE",   "name": "Energy",      "section": "us_sectors", "currency": "USD", "native": "USD"},
    {"ticker": "XLF",   "name": "Finance",     "section": "us_sectors", "currency": "USD", "native": "USD"},
    {"ticker": "XLV",   "name": "Health",      "section": "us_sectors", "currency": "USD", "native": "USD"},
    {"ticker": "XLRE",  "name": "Real Estate", "section": "us_sectors", "currency": "USD", "native": "USD"},
    {"ticker": "ITA",   "name": "Defence",     "section": "us_sectors", "currency": "USD", "native": "USD"},
    {"ticker": "UFO",   "name": "Space",       "section": "us_sectors", "currency": "USD", "native": "USD"},
]

# Yahoo Finance FX tickers: X/USD rate
FX_TICKERS = {
    "AUD": "AUDUSD=X",
    "CNY": "CNYUSD=X",
    "INR": "INRUSD=X",
}

# Maps API period param -> (yfinance period, yfinance interval)
PERIOD_MAP = {
    "1d": ("1d",  "5m"),
    "1w": ("5d",  "1h"),
    "1m": ("1mo", "1d"),
    "3m": ("3mo", "1d"),
    "1y": ("1y",  "1d"),
    # Warmup variants — same interval, extended lookback for BB seeding
    "1d_warmup": ("5d",  "5m"),
    "1w_warmup": ("1mo", "1h"),
    "1m_warmup": ("3mo", "1d"),
    "3m_warmup": ("1y",  "1d"),
    "1y_warmup": ("2y",  "1d"),
}


def _get_fx_rate(native_currency: str) -> float:
    """Return the current X-to-USD rate for a given native currency."""
    if native_currency == "USD":
        return 1.0
    fx_ticker = FX_TICKERS.get(native_currency)
    if not fx_ticker:
        return 1.0
    try:
        fi = yf.Ticker(fx_ticker).fast_info
        rate = fi.last_price
        return float(rate) if rate else 1.0
    except Exception:
        return 1.0


def _fetch_quote(ticker_sym: str) -> tuple[float | None, float | None]:
    """Return (last_price, change_percent) in the ticker's native currency."""
    try:
        fi = yf.Ticker(ticker_sym).fast_info
        price = fi.last_price
        prev_close = fi.previous_close
        if price is not None and prev_close and prev_close != 0:
            return round(price, 2), round(((price - prev_close) / prev_close) * 100, 2)
    except Exception:
        pass

    # Fallback: derive from recent daily history
    hist = yf.Ticker(ticker_sym).history(period="5d", interval="1d")
    closes = hist["Close"].dropna()
    if len(closes) >= 2:
        price = round(float(closes.iloc[-1]), 2)
        prev = float(closes.iloc[-2])
        return price, round(((price - prev) / prev) * 100, 2)
    if len(closes) == 1:
        return round(float(closes.iloc[-1]), 2), None
    return None, None


def get_indices() -> list[dict]:
    results = []
    fx_cache: dict[str, float] = {}

    for instrument in INSTRUMENTS:
        ticker = instrument["ticker"]
        native = instrument["native"]
        try:
            price, change_percent = _fetch_quote(ticker)

            if price is not None and native != "USD":
                if native not in fx_cache:
                    fx_cache[native] = _get_fx_rate(native)
                price = round(price * fx_cache[native], 2)

            results.append({
                "ticker": ticker,
                "name": instrument["name"],
                "section": instrument["section"],
                "currency": instrument["currency"],
                "price": price,
                "change_percent": change_percent,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
        except Exception as exc:
            results.append({
                "ticker": ticker,
                "name": instrument["name"],
                "section": instrument["section"],
                "currency": instrument["currency"],
                "price": None,
                "change_percent": None,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "error": str(exc),
            })
    return results


def get_index_history(ticker: str, period: str = "1m") -> list[dict]:
    instrument = next((i for i in INSTRUMENTS if i["ticker"] == ticker), None)
    native = instrument["native"] if instrument else "USD"

    yf_period, interval = PERIOD_MAP.get(period, ("1mo", "1d"))
    hist = yf.Ticker(ticker).history(period=yf_period, interval=interval)
    hist = hist.dropna(subset=["Close"])

    if native != "USD":
        fx_ticker = FX_TICKERS.get(native)
        if fx_ticker:
            fx_hist = yf.Ticker(fx_ticker).history(period=yf_period, interval=interval)
            fx_hist = fx_hist.dropna(subset=["Close"])
            # Align FX rates to the index's timestamps, forward-filling any gaps
            fx_rates = fx_hist["Close"].reindex(hist.index, method="ffill").fillna(
                fx_hist["Close"].iloc[-1] if len(fx_hist) else 1.0
            )
            for col in ["Open", "High", "Low", "Close"]:
                hist[col] = hist[col] * fx_rates

    return [
        {
            "timestamp": index.isoformat(),
            "open":  round(float(row["Open"]),  2),
            "high":  round(float(row["High"]),  2),
            "low":   round(float(row["Low"]),   2),
            "close": round(float(row["Close"]), 2),
        }
        for index, row in hist.iterrows()
    ]
