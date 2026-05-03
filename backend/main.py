from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from services.indices import get_indices, get_index_history, INSTRUMENTS
from services.crypto import get_crypto, get_crypto_history, COINS

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
