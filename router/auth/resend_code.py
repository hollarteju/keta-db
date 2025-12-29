from sqlalchemy.future import select
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from models import User
from schemas import ResendCompanyCode
from database import get_db
from utils.email_config import send_email
import random
from datetime import datetime, timedelta


router = APIRouter(
    prefix="/api/v1",
    tags=["users"]
)

@router.post("/resend-verification")
async def resend_verification_email(company: ResendCompanyCode, db: AsyncSession = Depends(get_db)):
    
    result = await db.execute(select(User).filter(User.email == company.email))
    existing_user = result.scalar_one_or_none()
    
    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="company not found"
        )

    if existing_user.verified_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your account has been verified"
        )
    
    token = f"{random.randint(0, 9999):04}"
    token_expires_at = datetime.utcnow() + timedelta(minutes=10)

    existing_user.token = token
    existing_user.token_expires_at = token_expires_at

    await db.commit()
    await db.refresh(existing_user)

    
    await send_email(existing_user.email, str(token), "company_verification")
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Verification email resent successfully"}
    )