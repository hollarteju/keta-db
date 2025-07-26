from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models import Companies
from sqlalchemy.future import select
import random
from datetime import datetime, timedelta
from utils.forgotten_config import forgotten_password_verification
from utils.email_config import send_email
from fastapi.responses import JSONResponse




router = APIRouter(
    prefix="/api/v1",
    tags=["companies"]
)

@router.post("/companies/forgotten_password")
async def forgotten_password_reset_email(email: str, db: AsyncSession = Depends(get_db)):
  
    result = await db.execute(select(Companies).filter(Companies.email == email))
    existing_company_email =  result.scalar_one_or_none()
    if not existing_company_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="email not exist"
        )
    
    token = f"{random.randint(0, 9999):04}"
    token_expires_at = datetime.utcnow() + timedelta(minutes=10)
    
    existing_company_email.token = token
    existing_company_email.token_expires_at = token_expires_at
    
    await db.commit()
    await db.refresh(existing_company_email)

    await send_email(existing_company_email.email, str(token), "forgotten_password.html")

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Reset password sent successfully"}
    )


@router.patch("/companies/forgotten_password")
async def forgotten_password_update(email: str, reset_token: str, password: str, db: AsyncSession = Depends(get_db)):
  
    result = await db.execute(select(Companies).filter(Companies.email == email, Companies.token == reset_token))
    company_exist =  result.scalar_one_or_none()

    if not company_exist:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="reset password failed"
        )
    
    try:
        company_exist.validate_token(reset_token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail=str(e)
        )

    hashed_password = Companies.hash_password(password)

    company_exist.password = hashed_password
    company_exist.token = None
    company_exist.token_expires_at = None
   
    await db.commit()
    await db.refresh(company_exist)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Reset password successfully"}
    )
