from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from database import get_db
from utils.dependencies.auth import get_current_user
from dotenv import load_dotenv
import os
import requests

load_dotenv()

router = APIRouter(
    prefix="/api/v1",
    tags=["webhooks"]
)

DEEPIDV_WEBHOOK_SECRET="eEhJDh2PpD91cXTE3g23x3c3XTLAAubT1baihzCP"

@router.post("/deepidv")
async def deepidv_webhook(
    request: Request,
    signature: str | None = Header(default=DEEPIDV_WEBHOOK_SECRET, alias="whsec_KH5FMwJzcJKnK0c-u_jjnP1Nx2Z8ZekX"),
):
    print("webhook endpoints: here!")
    webhook_secret = DEEPIDV_WEBHOOK_SECRET

    if signature != webhook_secret:
        raise HTTPException(
            status_code=401,
            detail="Invalid signature",
        )

    # 2. Get webhook payload
    event = await request.json()

    event_type = event.get("type")
    data = event.get("data")

    print(f"This is webhook data details: {data}")

    # 3. Process the event
    if event_type == "session.status.submitted":
        print(f"Session submitted: {data.get('id')}")

    elif event_type == "session.status.verified":
        print(f"Session verified: {data.get('id')}")

    elif event_type == "session.status.rejected":
        print(f"Session rejected: {data.get('id')}")

    elif event_type == "session.status.failed":
        print(f"Session failed: {data.get('id')}")

    elif event_type == "session.created":
        print(f"Session created: {data.get('id')}")

    else:
        print(f"Unhandled event type: {event_type}")

    # 4. Return 200 immediately
    return {"received": True}