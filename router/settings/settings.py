from fastapi import APIRouter, HTTPException, status, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import User, Settings
from schemas import UserSettingsResponse, UserSettingsUpdate, AuthenticatorVerifyRequest, KYCStartRequest
from database import get_db
from utils.dependencies.auth import get_current_user
import pyotp
import qrcode
import io
import base64


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



@router.get("/", response_model=UserSettingsResponse)
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

    return settings


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
        "qr_code": setup["qr_code"],
    }


@router.post("/settings/2fa/authenticator/verify")
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


@router.post("/kyc/start")
async def start_kyc(
    payload: KYCStartRequest,
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
    settings.session_id = payload.reference_id
    await db.commit()
    await db.refresh(settings)

    return {
        "message": "KYC session started successfully",
        "session_id": settings.session_id,
    }


DEEPIDV_WEBHOOK_SECRET="eEhJDh2PpD91cXTE3g23x3c3XTLAAubT1baihzCP"

@router.post("/deepidv-webhook")
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