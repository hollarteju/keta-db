import requests
from dotenv import load_dotenv
import os
import httpx


load_dotenv()
FLUTTERWAVE_BASE_URL = 'https://f4bexperience.flutterwave.com'
# FLUTTERWAVE_BASE_URL = "https://developersandbox-api.flutterwave.com"
FLUTTERWAVE_AUTH = "https://idp.flutterwave.com/realms/flutterwave/protocol/openid-connect/token"


def get_flutterwave_token():
    url = FLUTTERWAVE_AUTH
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = {
        "client_id": os.getenv("PRODUCTION_CLIENT_ID"),
        "client_secret": os.getenv("PRODUCTION_CLIENT_SECRET"),
        "grant_type": "client_credentials"
    }

    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status() 
        return response.json()

    except requests.exceptions.RequestException as e:
        return None


async def get_banks(country: str = "NG"):
    async with httpx.AsyncClient() as client:
        TOKEN = get_flutterwave_token()
        
        resp = await client.get(
            f"{FLUTTERWAVE_BASE_URL}/banks",
            params={"country": country},
            headers={
                "accept": "application/json",
                "Authorization": f"Bearer {TOKEN.get("access_token")}"
            }
        )
        data = resp.json()
    return data.get("data", [])

async def verify_account(account: str, bank_code: str, currency: str):
    async with httpx.AsyncClient() as client:
        token_data = get_flutterwave_token()
        access_token = token_data.get("access_token")

        payload = {
            "account": {
                "code": bank_code,
                "number": account
            },
            "currency": currency
        }

        resp = await client.post(
            f"{FLUTTERWAVE_BASE_URL}/banks/account-resolve",
            json=payload,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
        )
        return resp.json()





async def initiate_bank_transfer(
    account_number: str,
    bank_code: str,
    amount: float,
    source_currency: str = "NGN",
    destination_currency: str = "NGN",
    action: str = "instant",
):
    token_data = get_flutterwave_token()
    access_token = token_data.get("access_token")

    url = f"{FLUTTERWAVE_BASE_URL}/direct-transfers"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "action": action,
        "type": "bank",
        "payment_instruction": {
            "source_currency": source_currency,
            "amount": {
                "applies_to": "source_currency",
                "value": amount
            },
            "recipient": {
                "bank": {
                    "account_number": account_number,
                    "code": bank_code
                }
            },
            "destination_currency": destination_currency
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)

        response.raise_for_status()
        return response.json()


# 201 {'status': 'success', 'message': 'Transfer created', 'data': {'id': 'trf_C9Vtg6BTow9E5ybgA0QwM', 'type': 'bank', 'action': 'instant', 'reference': 'flw_63CNdvUctk', 'status': 'NEW', 'source_currency': 'NGN', 'destination_currency': 'NGN', 'amount': {'value': 200.0, 'applies_to': 'source_currency'}, 'recipient': {'type': 'bank', 'id': 'rcb_G5QHX1Mult', 'name': {'first': 'SARUMI', 'last': 'ADEMIJU'}, 'currency': 'NGN', 'bank': {'account_number': '0007218920', 'code': '058'}}, 'meta': {}, 'created_datetime': '2026-04-26T14:28:11.124Z'}}

# https://keta-db-05ke.onrender.com
