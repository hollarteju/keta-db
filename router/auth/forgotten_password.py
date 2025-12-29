from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models import User
from sqlalchemy.future import select
import random
from datetime import datetime, timedelta
from utils.forgotten_config import forgotten_password_verification
from utils.email_config import send_email
from fastapi.responses import JSONResponse




router = APIRouter(
    prefix="/api/v1",
    tags=["users"]
)

@router.post("/users/forgotten_password")
async def forgotten_password_reset_email(email: str, db: AsyncSession = Depends(get_db)):
  
    result = await db.execute(select(User).filter(User.email == email))
    existing_user_email =  result.scalar_one_or_none()
    if not existing_user_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="email not exist"
        )
    
    token = f"{random.randint(0, 9999):04}"
    token_expires_at = datetime.utcnow() + timedelta(minutes=10)
    
    existing_user_email.token = token
    existing_user_email.token_expires_at = token_expires_at
    
    await db.commit()
    await db.refresh(existing_user_email)

    await send_email(existing_user_email.email, str(token), "company_verification")

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Reset password sent successfully"}
    )


@router.patch("/users/forgotten_password")
async def forgotten_password_update(email: str, reset_token: str, password: str, db: AsyncSession = Depends(get_db)):
  
    result = await db.execute(select(User).filter(User.email == email, User.token == reset_token))
    user_exist =  result.scalar_one_or_none()

    if not user_exist:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="reset password failed"
        )
    
    try:
        user_exist.validate_token(reset_token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail=str(e)
        )

    hashed_password = User.hash_password(password)

    user_exist.password = hashed_password
    user_exist.token = None
    user_exist.token_expires_at = None
   
    await db.commit()
    await db.refresh(user_exist)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Reset password successfully"}
    )
