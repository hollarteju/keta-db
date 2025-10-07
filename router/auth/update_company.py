from uuid import UUID
from sqlalchemy import update
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.future import select
from models import Companies
from schemas import UpdateCompanyResponse, UpdateCompany
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from utils.uuid_convert import uuid_to_str, str_to_uuid


router = APIRouter(
    prefix="/api/v1",
    tags=["companies"]
)

@router.put("/update/{company_id}")
async def update_company(company_id: UUID, company_data: UpdateCompany, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(Companies).where(Companies.id == uuid_to_str(company_id)))
        company = result.scalar_one_or_none()

        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found"
            )
        

        if not company.verified_email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email not verified. Please verify your email before updating your company details."
            )

        for field, value in company_data.model_dump(exclude_unset=True).items():
            setattr(company, field, value)


        await db.commit()
        await db.refresh(company)

        return {
            "status": "success",
            "message": "Company updated successfully",
            "company": company
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update company: {e}"
        )
