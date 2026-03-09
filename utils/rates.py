import httpx
from fastapi import HTTPException, APIRouter, Query


EXCHANGE_API_KEY = "be4de475e381c42fe5c9ea71dd474599"
EXCHANGE_BASE_URL = "https://api.exchangeratesapi.io/v1"



async def fetch_rates(symbols: list[str]):
    url = f"{EXCHANGE_BASE_URL}/latest"

    params = {
        "access_key": EXCHANGE_API_KEY,
        "symbols": ",".join(symbols)
    }

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, params=params)

    data = resp.json()

    if not data.get("success", False):
        raise HTTPException(400, data.get("error", {}).get("info", "Rate fetch failed"))

    return data.get("rates", {})

async def fetch_currency_rates(base: str, symbol: str):
    url = f"{EXCHANGE_BASE_URL}/latest"

    params = {
        "access_key": EXCHANGE_API_KEY,
        "base": base.upper(),
        "symbols": symbol.upper()
    }

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, params=params)

    if resp.status_code != 200:
        raise HTTPException(502, "Exchange service unavailable")

    data = resp.json()

    if not data.get("success", False):
        raise HTTPException(
            400,
            data.get("error", {}).get("info", "Failed to fetch exchange rates")
        )

    return data
