from fastapi import APIRouter, HTTPException, status, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import User, Settings, KYCVerification
from schemas import UserSettingsResponse, UserSettingsUpdate, AuthenticatorVerifyRequest, KYCStartRequest
from database import get_db
from utils.dependencies.auth import get_current_user
import pyotp
import qrcode
import io
import base64
import os
import httpx

router = APIRouter(
    prefix="/api/v1/settings",
    tags=["settings"]
)

def create_authenticator_setup(email: str):
    secret = pyotp.random_base32()

    totp = pyotp.TOTP(secret)

    otp_uri = totp.provisioning_uri(
        name=email,
        issuer_name="keta",
    )

    qr = qrcode.make(otp_uri)

    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")

    qr_base64 = base64.b64encode(
        buffer.getvalue()
    ).decode("utf-8")

    return {
        "secret": secret,
        "otp_uri": otp_uri,
        "qr_code": f"data:image/png;base64,{qr_base64}",
    }



@router.get("/")
async def get_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Settings).where(Settings.user_id == current_user.id)
    )

    settings = result.scalar_one_or_none()

    if not settings:
        raise HTTPException(
            status_code=404,
            detail="User settings not found"
        )

    kyc_result = await db.execute(
            select(KYCVerification).where(
                KYCVerification.user_id == current_user.id
            )
        )
    
    kyc = kyc_result.scalar_one_or_none()

    return {"settings": settings, "kyc": kyc}


@router.put(
    "/",
    response_model=UserSettingsResponse
)
async def update_settings(
    data: UserSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
            select(Settings).where(Settings.user_id == current_user.id)
        )
    
    settings = result.scalar_one_or_none()

    if not settings:
        raise HTTPException(
            status_code=404,
            detail="User settings not found"
        )

    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(settings, field, value)

    db.commit()
    db.refresh(settings)

    return settings


@router.post("/2fa/authenticator/setup")
async def setup_authenticator(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    setup = create_authenticator_setup(current_user.email)

    result = await db.execute(
        select(Settings).where(
            Settings.user_id == current_user.id
        )
    )

    settings = result.scalar_one_or_none()

    if not settings:
        raise HTTPException(
            status_code=404,
            detail="User settings not found",
        )

    # Store the secret temporarily
    settings.authenticator_secret = setup["secret"]

    await db.commit()

    return {
        "message": "Authenticator setup initialized",
        "otp_uri": setup["otp_uri"],
        "otp_secret": setup["secret"],
        "qr_code": setup["qr_code"],
    }


@router.post("/2fa/authenticator/verify")
async def verify_authenticator(
    payload: AuthenticatorVerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Settings).where(
            Settings.user_id == current_user.id
        )
    )

    settings = result.scalar_one_or_none()

    if not settings:
        raise HTTPException(
            status_code=404,
            detail="User settings not found",
        )

    if not settings.authenticator_secret:
        raise HTTPException(
            status_code=400,
            detail="Authenticator setup has not been initialized",
        )

    totp = pyotp.TOTP(settings.authenticator_secret)

    if not totp.verify(payload.code):
        raise HTTPException(
            status_code=400,
            detail="Invalid authenticator code",
        )

    settings.authenticator_2fa_verified = True
    settings.two_factor_enabled = True

    # If this is the first 2FA method
    settings.two_factor_methods = ["authenticator"]

    await db.commit()

    return {
        "message": "Authenticator 2FA enabled successfully",
        "two_factor_enabled": True,
        "two_factor_methods": settings.two_factor_methods,
    }



@router.post("/kyc/session")
async def create_kyc_session(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    api_key = "5HKrRYuBPL6PWRI0ssEuD3yYZ3Z1xDn81nYLljqy"

    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="DEEPIDV_KEY is not configured",
        )

    deepidv_payload = {
        "firstName": current_user.first_name,
        "lastName": current_user.last_name,
        "email": current_user.email,
        "phone": "+2347052490998",
        "externalId": current_user.id,
        "redirect_url": "https://observer-egotistic-exorcism.ngrok-free.dev/api/v1/setting/deepidv-webhook",
        "expires_in_hours": 48,
    }

    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.deepidv.com/v1/sessions",
                headers=headers,
                json=deepidv_payload,
            )

    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Unable to connect to DeepIDV: {str(exc)}",
        )

    if response.status_code >= 400:
        try:
            error_data = response.json()
        except Exception:
            error_data = response.text

        raise HTTPException(
            status_code=response.status_code,
            detail={
                "message": "DeepIDV session creation failed",
                "deepidv_response": error_data,
            },
        )

    deepidv_data = response.json()

    session_id = deepidv_data.get("id")

    if not session_id:
        raise HTTPException(
            status_code=502,
            detail="DeepIDV did not return a session ID",
        )

    print(deepidv_data.session_url)

    return {
        "message": "KYC session created successfully",
        "session_id": session_id,
        "external_id": current_user.id,
        "status": deepidv_data.get("status"),
        "session_progress": deepidv_data.get("session_progress"),
        "deepidv_response": deepidv_data,
    }


@router.post("/deepidv-webhook")
async def deepidv_webhook(
    request: Request,
    signature: str | None = Header(default=os.getenv("DEEPIDV_WEBHOOK_SECRET"), alias=os.getenv("DEEPDIV_WEBHOOK_KEY")),
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


# @router.post("/deepidv-webhook")
# async def deepidv_webhook(
#     request: Request,
#     db: AsyncSession = Depends(get_db),
#     signature: str | None = Header(
#         default=None,
#         alias="whsec_....",
#     ),
# ):
#     print("Webhook endpoint: here!")

#     # 1. Validate webhook signature
#     webhook_secret = DEEPIDV_WEBHOOK_SECRET

#     if signature != webhook_secret:
#         raise HTTPException(
#             status_code=401,
#             detail="Invalid signature",
#         )

#     # 2. Get webhook payload
#     event = await request.json()

#     event_type = event.get("type")
#     data = event.get("data") or {}

#     session_id = data.get("id")

#     print(f"Webhook event: {event_type}")
#     print(f"DeepIDV session ID: {session_id}")
#     print(f"Webhook data: {data}")

#     if not session_id:
#         raise HTTPException(
#             status_code=400,
#             detail="Session ID missing from webhook",
#         )

#     # 3. Find user's settings using DeepIDV session ID
#     result = await db.execute(
#         select(Settings).where(
#             Settings.session_id == session_id
#         )
#     )

#     settings = result.scalar_one_or_none()

#     if not settings:
#         print(
#             f"No user found for DeepIDV session: {session_id}"
#         )

#         # Return 200 so DeepIDV doesn't repeatedly retry
#         return {
#             "received": True,
#             "message": "User session not found",
#         }

#     # 4. Find the user
#     user_result = await db.execute(
#         select(User).where(
#             User.id == settings.user_id
#         )
#     )

#     user = user_result.scalar_one_or_none()

#     if not user:
#         print(
#             f"User not found: {settings.user_id}"
#         )

#         return {
#             "received": True,
#             "message": "User not found",
#         }

#     # 5. Save KYC status
#     if event_type == "session.status.submitted":
#         user.kyc_status = "submitted"

#     elif event_type == "session.status.verified":
#         user.kyc_status = "verified"

#     elif event_type == "session.status.rejected":
#         user.kyc_status = "rejected"

#     elif event_type == "session.status.failed":
#         user.kyc_status = "failed"

#     elif event_type == "session.created":
#         user.kyc_status = "pending"

#     else:
#         print(f"Unhandled event type: {event_type}")

#     # 6. Save changes
#     await db.commit()

#     print(
#         f"KYC updated for user {user.id}: "
#         f"{user.kyc_status}"
#     )

#     # 7. Acknowledge webhook
#     return {
#         "received": True,
#     }