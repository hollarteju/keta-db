import httpx
from fastapi import HTTPException, APIRouter, Query
from utils.rates import fetch_currency_rates, fetch_rates


router = APIRouter(prefix="/rate", tags=["Currency"])


@router.get("/rates")
async def get_currency_rate(
    from_currency: str = Query(..., description="Currency to convert from e.g USD"),
    to_currency: str = Query(..., description="Currency to convert to e.g NGN")
):

    data = await fetch_currency_rates(from_currency, to_currency)

    rates = data.get("rates", {})
    rate = rates.get(to_currency.upper())

    if not rate:
        raise HTTPException(404, f"Currency {to_currency} not found")

    return {
        "base": from_currency.upper(),
        "currency": to_currency.upper(),
        "rate": rate,
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

    rate_used = rate_to / rate_from
    converted = amount * rate_used

    return {
        "from": from_currency,
        "to": to_currency,
        "amount": amount,
        "rate_used": rate_used,
        "converted_amount": round(converted, 2)
    }