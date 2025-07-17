import smtplib
from email.message import EmailMessage
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI
from pathlib import Path
import os
from dotenv import load_dotenv


app = FastAPI()
load_dotenv()

templates = Jinja2Templates(directory="templates")  # Ensure this folder contains your HTML files
EMAIL= os.getenv("EMAIL")
EMAIL_PASSWORD= os.getenv("EMAIL_PASSWORD")


async def forgotten_password_verification(recipient_email: str, token: str ):
    email_address = EMAIL
    email_password = EMAIL_PASSWORD

    template = templates.get_template("forgotten_password.html")  
    html_body = template.render(token=token)  

    msg = EmailMessage()
    msg["Subject"] = "Password Reset Request"
    msg["From"] = email_address
    msg["To"] = recipient_email
    msg.add_alternative(html_body, subtype="html") 

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(email_address, email_password)
            smtp.send_message(msg)
            return {"message": "Email sent successfully"}
    except Exception as e:
        return {"error": str(e)}
