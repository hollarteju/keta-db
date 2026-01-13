import os
from dotenv import load_dotenv
import httpx
load_dotenv()


PLUNK_API_URL = "https://api.useplunk.com/v1/track"
PLUNK_API_KEY = os.getenv("PLUNK_EMAIL_API")

async def send_email(user_email: str, otp: str, event_name: str) -> dict:
    headers = { 
        "Content-Type": "application/json",
        "Authorization": f"Bearer {PLUNK_API_KEY}"
    }

    payload = {
        "event": event_name,
        "email": user_email,
        "data": {
            "otp": otp
        }
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(PLUNK_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        return {"error": str(e)}
