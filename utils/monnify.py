import os
import httpx
from uuid import uuid4

MONNIFY_API_KEY = os.getenv("MONNIFY_API_KEY")
MONNIFY_SECRET_KEY = os.getenv("MONNIFY_SECRET_KEY")
MONNIFY_CONTRACT_CODE = os.getenv("MONNIFY_CONTRACT_CODE")

async def initiate_monnify_payment(user_id: str, amount: float):
    reference = str(uuid4())
    url = "https://api.monnify.com/api/v1/merchant/transactions/init-transaction"

    headers = {
        "Authorization": f"Basic {MONNIFY_API_KEY}:{MONNIFY_SECRET_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "amount": amount,
        "customerName": user_id,
        "customerEmail": f"{user_id}@example.com",
        "paymentReference": reference,
        "contractCode": MONNIFY_CONTRACT_CODE,
        "currencyCode": "NGN",
        "paymentDescription": "Wallet funding"
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload, headers=headers)
        data = resp.json()
    
    return data  # contains payment URL for frontend
