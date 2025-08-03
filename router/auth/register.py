from sqlalchemy.future import select
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from models import Companies
from schemas import CreateCompany, CompanyResponse, RegisterCompanyResponse
from database import get_db
from utils.email_config import send_email
import random
from datetime import datetime, timedelta




router = APIRouter(
    prefix="/api/v1",
    tags=["companies"]
)

@router.post("/companies/register", response_model=RegisterCompanyResponse)
async def create_company(company: CreateCompany, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(Companies).filter(Companies.email == company.email))
        existing_company_email =  result.scalar_one_or_none()
        
        if existing_company_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="email already taken by another company"
            )
        
        hashed_password = Companies.hash_password(company.password)

        token = f"{random.randint(0, 9999):04}"
        token_expires_at = datetime.utcnow() + timedelta(minutes=10)


        new_company = Companies(
            email=company.email,
            password=hashed_password,  
            token = token,
            token_expires_at=token_expires_at
        )

        db.add(new_company)
        await db.commit()
        await db.refresh(new_company)

        await send_email(company.email, str(token), "verification_email.html")

        return RegisterCompanyResponse(
            status="success",
            message="Company registered successfully",
            company=CompanyResponse.model_validate(new_company)
        )

    except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unexpected error during company registration: {e}."
            )
