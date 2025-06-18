import smtplib
from email.message import EmailMessage
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI
from pathlib import Path

app = FastAPI()

templates = Jinja2Templates(directory="templates")  # Ensure this folder contains your HTML files

async def send_email(recipient_email: str, token: str ):
    email_address = "sirolateju2022@gmail.com"
    email_password = "eeir ngxg ubos ggdi"

    template = templates.get_template("verification_email.html")  
    html_body = template.render(token=token)  

    msg = EmailMessage()
    msg["Subject"] = "Verify Account"
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
