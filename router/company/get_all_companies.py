from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from schemas import AllCompanyResponse, StaffResponse
from fastapi.responses import JSONResponse
from models import Companies, CompanyStaffs
from sqlalchemy.orm import selectinload


router = APIRouter(
    prefix="/api/v1",
    tags=["companies"]
)


@router.get("/companies/all_companies", response_model=list[AllCompanyResponse])
async def get_all_companies(db: AsyncSession = Depends(get_db)):
    try:
        all_companies = select(Companies)
        result = await db.execute(all_companies)
        companies = result.scalars().all()
        if not companies:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No companies found",
            )
                
        return companies
        

        

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Connect to a strong network {e}",
            headers={"X-Error": str(e)},
        )
    
