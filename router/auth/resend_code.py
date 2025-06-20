from sqlalchemy.future import select
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from models import Companies
from schemas import ResendCompanyCode
from database import get_db
from utils.email_config import send_email


router = APIRouter(
    prefix="/api/v1",
    tags=["companies"]
)

@router.post("/resend-verification")
async def resend_verification_email(company: ResendCompanyCode, db: AsyncSession = Depends(get_db)):

    result = await db.execute(select(Companies).filter(Companies.email == company.email))
    existing_company = result.scalar_one_or_none()

    if not existing_company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="company not found"
        )

    if existing_company.verified_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your account has been verified"
        )
    
    await send_email(existing_company.email, str(existing_company.id))
   
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Verification email resent successfully"}
    )