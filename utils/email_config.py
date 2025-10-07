import smtplib
from email.message import EmailMessage
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI
from pathlib import Path
import os
from dotenv import load_dotenv


app = FastAPI()
load_dotenv()

# templates = Jinja2Templates(directory="templates")  # Ensure this folder contains your HTML files
# EMAIL= os.getenv("EMAIL")
# EMAIL_PASSWORD= os.getenv("EMAIL_PASSWORD")

# async def send_email(recipient_email: str, token: str, html_template: str ):
#     email_address = EMAIL
#     email_password = EMAIL_PASSWORD

#     template = templates.get_template(html_template)  
#     html_body = template.render(token=token)  

#     msg = EmailMessage()
#     msg["Subject"] = "Verify Account"
#     msg["From"] = email_address
#     msg["To"] = recipient_email
#     msg.add_alternative(html_body, subtype="html") 

#     try:
#         with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
#             smtp.login(email_address, email_password)
#             smtp.send_message(msg)
#             return {"message": "Email sent successfully"}
#     except Exception as e:
#         return {"error": str(e)}

import httpx

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
