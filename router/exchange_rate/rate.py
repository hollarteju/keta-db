import httpx
from fastapi import HTTPException, APIRouter, Query

EXCHANGE_API_KEY = "be4de475e381c42fe5c9ea71dd474599"
EXCHANGE_BASE_URL = "https://api.exchangeratesapi.io/v1"

router = APIRouter(prefix="/rate", tags=["Currency"])

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

async def fetch_currency_rates(symbols: str | None = None):
    url = f"{EXCHANGE_BASE_URL}/latest"

    params = {
        "access_key": EXCHANGE_API_KEY,
    }

    if symbols:
        params["symbols"] = symbols.upper()

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


@router.get("/rates")
async def get_currency_rates(
    symbol: str | None = Query(None, description="Currency e.g. NGN, USD")
):
    symbols = symbol if symbol else "USD,NGN,GBP"

    data = await fetch_currency_rates(symbols)

    rates = data.get("rates", {})

    if symbol:
        rate = rates.get(symbol.upper())
        if not rate:
            raise HTTPException(404, f"Currency {symbol} not found")

        return {
            "base": "EUR",
            "currency": symbol.upper(),
            "rate": rate
        }

    return {
        "base": "EUR",
        "rates": rates,
        "timestamp": data.get("timestamp")
    }

@router.get("/convert")
async def convert_currency(
    amount: float = Query(..., gt=0),
    from_currency: str = Query(..., min_length=3, max_length=3),
    to_currency: str = Query(..., min_length=3, max_length=3),
):
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    # Request both currencies at once
    rates = await fetch_rates([from_currency, to_currency])

    rate_from = rates.get(from_currency)
    rate_to = rates.get(to_currency)

    if not rate_from or not rate_to:
        raise HTTPException(404, "Currency not supported")

    # EUR base conversion
    # amount_in_eur = amount / rate_from
    # converted = amount_in_eur * rate_to
    rate_used = rate_to / rate_from
    converted = amount * rate_used

    return {
        "from": from_currency,
        "to": to_currency,
        "amount": amount,
        "rate_used": rate_used,
        "converted_amount": round(converted, 2)
    }