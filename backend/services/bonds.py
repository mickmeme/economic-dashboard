import yfinance as yf
from datetime import datetime, timezone

BONDS = [
    {"ticker": "RGB.AX",  "name": "AU Government Bonds",       "section": "bonds", "currency": "AUD"},
    {"ticker": "ILB.AX",  "name": "AU Treasury Indexed Bonds", "section": "bonds", "currency": "AUD"},
    {"ticker": "IEF",     "name": "US Government Bonds",       "section": "bonds", "currency": "USD"},
    {"ticker": "1488.T",  "name": "Japanese Govt Bonds",       "section": "bonds", "currency": "JPY"},
]

PERIOD_MAP = {
    "1d":        ("1d",  "5m"),
    "1w":        ("5d",  "1h"),
    "1m":        ("1mo", "1d"),
    "3m":        ("3mo", "1d"),
    "1y":        ("1y",  "1d"),
    "1d_warmup": ("5d",  "5m"),
    "1w_warmup": ("1mo", "1h"),
    "1m_warmup": ("3mo", "1d"),
    "3m_warmup": ("1y",  "1d"),
    "1y_warmup": ("2y",  "1d"),
}


def _fetch_quote(ticker_sym: str) -> tuple[float | None, float | None]:
    try:
        fi = yf.Ticker(ticker_sym).fast_info
        price = fi.last_price
        prev_close = fi.previous_close
        if price is not None and prev_close and prev_close != 0:
            return round(price, 2), round(((price - prev_close) / prev_close) * 100, 2)
    except Exception:
        pass

    hist = yf.Ticker(ticker_sym).history(period="5d", interval="1d")
    closes = hist["Close"].dropna()
    if len(closes) >= 2:
        price = round(float(closes.iloc[-1]), 2)
        prev = float(closes.iloc[-2])
        return price, round(((price - prev) / prev) * 100, 2)
    if len(closes) == 1:
        return round(float(closes.iloc[-1]), 2), None
    return None, None


def get_bonds() -> list[dict]:
    results = []
    for bond in BONDS:
        ticker = bond["ticker"]
        try:
            price, change_percent = _fetch_quote(ticker)
            results.append({
                "ticker": ticker,
                "name": bond["name"],
                "section": bond["section"],
                "currency": bond["currency"],
                "price": price,
                "change_percent": change_percent,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
        except Exception as exc:
            results.append({
                "ticker": ticker,
                "name": bond["name"],
                "section": bond["section"],
                "currency": bond["currency"],
                "price": None,
                "change_percent": None,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "error": str(exc),
            })
    return results


def get_bond_history(ticker: str, period: str = "1m") -> list[dict]:
    yf_period, interval = PERIOD_MAP.get(period, ("1mo", "1d"))
    hist = yf.Ticker(ticker).history(period=yf_period, interval=interval)
    hist = hist.dropna(subset=["Close"])

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
