import requests
from dotenv import load_dotenv
import os
import httpx
from uuid import uuid4
# from core.encryption import encrypt_field
from schemas import DepositRequest

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

async def request_header(method: str, path: str, payload: dict = None):
    token_data = get_flutterwave_token()
    access_token = token_data.get("access_token")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Trace-Id": str(uuid4()),
        "X-Idempotency-Key": str(uuid4()),
    }

    timeout = httpx.Timeout(30.0, connect=10.0)

    async with httpx.AsyncClient(timeout=timeout) as client:

        method = method.lower()

        if method == "get":
            response = await client.get(
                f"{FLUTTERWAVE_BASE_URL}{path}",
                headers=headers,
                params=payload  # optional query params
            )

        else:
            response = await getattr(client, method)(
                f"{FLUTTERWAVE_BASE_URL}{path}",
                json=payload,
                headers=headers,
            )

        print("STATUS:", response.status_code)
        print("BODY:", response.text)

        response.raise_for_status()
        return response.json()
        

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
        print("Status:", response.status_code)
        print("Response:", response.text)
        response.raise_for_status()
        return response.json()


async def create_payment_link(amount: float, email: str):
    token_data = get_flutterwave_token()
    access_token = token_data.get("access_token")

    url = f"{FLUTTERWAVE_BASE_URL}/payments"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "tx_ref": f"tx-{uuid4()}",
        "amount": amount,
        "currency": "NGN",
        "redirect_url": "https://yourdomain.com/payment-success",
        "customer": {
            "email": email
        },
        "customizations": {
            "title": "Wallet Funding",
            "description": "Deposit into wallet"
        }
    }

    async with httpx.AsyncClient() as client:
        res = await client.post(url, json=payload, headers=headers)
        return res.json()



async def charge_card(amount, currency, customer, card, reference):
    nonce = str(uuid4())
    payload = {
        "amount": amount,
        "currency": currency,
        "reference": reference,
        "payment_method": {
            "type": "card",
            "card": {
                "encrypted_card_number": card.card_number,
                "encrypted_expiry_month": card.expiry_month,
                "encrypted_expiry_year": card.expiry_year,
                "encrypted_cvv": card.cvv,
                "nonce": nonce,
            },
        },
        "customer": {
            "email": customer.email,
            "name": {"first": customer.first_name, "last": customer.last_name},
        },
    }
    result = await request_header("post", "/orchestration/direct-charges", payload)

    return {
        "charge_id": result["data"]["id"],
        "next_action": result["data"].get("next_action"),
        "method": "card",
    }


async def charge_mobile_money(amount, currency, customer, mobile_money):
    payload = {
        "amount": amount,
        "currency": currency,
        "reference": str(uuid4()),
        "payment_method": {
            "type": "mobile_money",
            "mobile_money": {
                "phone_number": mobile_money.phone_number,
                "network": mobile_money.network,
                "country_code": mobile_money.country_code,
            },
        },
        "customer": {
            "email": customer.email,
            "name": {"first": customer.first_name, "last": customer.last_name},
        },
    }
    result = await request_header("post", "/orchestration/direct-charges", payload)
    return {
        "charge_id": result["data"]["id"],
        "next_action": result["data"].get("next_action"),  # payment_instruction — show "check your phone"
        "method": "mobile_money",
    }


async def create_customer(email, first_name, last_name, country_code, phone_number):
    payload = {
        "email": email,
        "name": {
            "first": first_name,
            "last": last_name
        },
        "phone": {
            "country_code": country_code,   # Nigeria — change per country
            "number": phone_number
        }
    }

    try:
            result = await request_header("post", "/customers", payload)
            return result["data"]["id"]

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 409:
            existing_id = await get_customer_by_email(email)

            if existing_id:
                return existing_id

        raise

async def get_customer_by_email(email: str):
    result = await request_header(
        "get",
        f"/customers?email={email}",
        None
    )

    data = result.get("data", [])
    if data:
        return data[0]["id"]

    return None

async def create_virtual_account(
    amount: float,
    currency: str,
    email: str,
    first_name: str,
    last_name: str,
    country_code: str,
    phone_number: str,
    reference: str
):
    customer_id = await create_customer(email, first_name, last_name, country_code, phone_number)

    payload = {
        "reference": reference,
        "amount": str(amount),
        "currency": currency,
        "customer_id": customer_id,
        "expiry": 180,
        "account_type": "dynamic",
        "narration": "Cornelius Ashley-Osuzoka"
    }

    response = await request_header(
        "post",
        "/virtual-accounts",
        payload
    )

    return response

async def charge_ussd(amount, currency, customer, ussd):
    payload = {
        "amount": amount,
        "currency": currency,
        "reference": str(uuid4()),
        "payment_method": {
            "type": "ussd",
            "ussd": {"account_bank": ussd.bank_code},
        },
        "customer": {
            "email": customer.email,
            "name": {"first": customer.first_name, "last": customer.last_name},
        },
    }
    result = await request_header("post", "/orchestration/direct-charges", payload)
    return {
        "charge_id": result["data"]["id"],
        "next_action": result["data"].get("next_action"),  # payment_instruction — show USSD code
        "method": "ussd",
    }




# 201 {'status': 'success', 'message': 'Transfer created', 'data': {'id': 'trf_C9Vtg6BTow9E5ybgA0QwM', 'type': 'bank', 'action': 'instant', 'reference': 'flw_63CNdvUctk', 'status': 'NEW', 'source_currency': 'NGN', 'destination_currency': 'NGN', 'amount': {'value': 200.0, 'applies_to': 'source_currency'}, 'recipient': {'type': 'bank', 'id': 'rcb_G5QHX1Mult', 'name': {'first': 'SARUMI', 'last': 'ADEMIJU'}, 'currency': 'NGN', 'bank': {'account_number': '0007218920', 'code': '058'}}, 'meta': {}, 'created_datetime': '2026-04-26T14:28:11.124Z'}}

# https://keta-db-05ke.onrender.com
