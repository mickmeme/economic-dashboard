from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from services.indices import get_indices, get_index_history, INSTRUMENTS
from services.crypto import get_crypto, get_crypto_history, COINS
from services.ratios import get_buffett_ratio, get_btc_gold_ratio
from services.yields import get_yield_spread
from services.realestate import get_state_overview, get_suburb_overview, get_recent_sales
from services.resources import get_resources_list, get_resource_history, VALID_KEYS as RESOURCE_KEYS
from services.bonds import get_bonds, get_bond_history, BONDS
from services.news import get_news, VALID_CATEGORIES as NEWS_CATEGORIES
from services.steam import get_new_releases as steam_get_new_releases
from services.central_bank_gold import get_central_bank_gold

app = FastAPI(title="Economic Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to your frontend URL after deployment
    allow_methods=["GET"],
    allow_headers=["*"],
)

VALID_PERIODS = {"1d", "1w", "1m", "3m", "1y", "1d_warmup", "1w_warmup", "1m_warmup", "3m_warmup", "1y_warmup"}
VALID_TICKERS = {i["ticker"] for i in INSTRUMENTS}
VALID_COIN_IDS = {c["id"] for c in COINS}
VALID_BOND_TICKERS = {b["ticker"] for b in BONDS}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/indices")
def indices():
    return get_indices()


@app.get("/api/indices/{ticker}/history")
def index_history(
    ticker: str,
    period: str = Query(default="1m", pattern="^(1d|1w|1m|3m|1y)(_(warmup))?$"),
):
    if ticker not in VALID_TICKERS:
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' not found")
    return get_index_history(ticker, period)


@app.get("/api/crypto")
def crypto():
    return get_crypto()


@app.get("/api/crypto/{coin_id}/history")
def crypto_history(
    coin_id: str,
    period: str = Query(default="1m", pattern="^(1d|1w|1m|3m|1y)(_(warmup))?$"),
):
    if coin_id not in VALID_COIN_IDS:
        raise HTTPException(status_code=404, detail=f"Coin '{coin_id}' not found")
    return get_crypto_history(coin_id, period)


@app.get("/api/bonds")
def bonds():
    return get_bonds()


@app.get("/api/bonds/{ticker}/history")
def bond_history(
    ticker: str,
    period: str = Query(default="1m", pattern="^(1d|1w|1m|3m|1y)(_(warmup))?$"),
):
    if ticker not in VALID_BOND_TICKERS:
        raise HTTPException(status_code=404, detail=f"Bond ticker '{ticker}' not found")
    return get_bond_history(ticker, period)


@app.get("/api/ratios/buffett")
def buffett_ratio(period: str = Query(default="10y", pattern="^(5y|10y|max)$")):
    return get_buffett_ratio(period)


@app.get("/api/ratios/btc-gold")
def btc_gold_ratio(period: str = Query(default="1y", pattern="^(1y|3y|max)$")):
    return get_btc_gold_ratio(period)


@app.get("/api/ratios/yield-spread")
def yield_spread(period: str = Query(default="5y", pattern="^(1y|3y|5y|10y|max)$")):
    return get_yield_spread(period)


@app.get("/api/resources")
def resources_list():
    try:
        return get_resources_list()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Resources unavailable: {exc}")


@app.get("/api/resources/{key}/history")
def resource_history(
    key: str,
    period: str = Query(default="1m", pattern="^(1d|1w|1m|3m|1y|5y)$"),
):
    if key not in RESOURCE_KEYS:
        raise HTTPException(status_code=404, detail=f"Resource '{key}' not found")
    try:
        return get_resource_history(key, period)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/api/realestate/states")
def realestate_states():
    try:
        return get_state_overview()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Real estate data unavailable: {exc}")


@app.get("/api/realestate/sales/{postcode}")
def realestate_sales(postcode: str):
    if not postcode.isdigit() or len(postcode) != 4:
        raise HTTPException(status_code=400, detail="postcode must be a 4-digit number")
    try:
        return get_recent_sales(postcode)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Sales data unavailable: {exc}")


@app.get("/api/realestate/suburbs")
def realestate_suburbs():
    try:
        return get_suburb_overview()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Real estate data unavailable: {exc}")


@app.get("/api/gold/central-bank")
def central_bank_gold(period: str = Query(default="5y", pattern="^(1y|3y|5y|10y|max)$")):
    try:
        return get_central_bank_gold(period)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Central bank gold data unavailable: {exc}")


@app.get("/api/steam/newreleases")
def steam_new_releases():
    try:
        return steam_get_new_releases()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Steam data unavailable: {exc}")


@app.get("/api/news/{category}")
def news(category: str):
    if category not in NEWS_CATEGORIES:
        raise HTTPException(status_code=404, detail=f"News category '{category}' not found")
    try:
        return get_news(category)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"News unavailable: {exc}")
