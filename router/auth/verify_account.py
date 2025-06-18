from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from models import Companies
from database import get_db
from sqlalchemy.future import select
from uuid import UUID
from fastapi.responses import JSONResponse


router = APIRouter(
    prefix="/api/v1",
    tags=["companies"]
)

@router.post("/companies/verify_email")
async def verify_account(id: UUID, token:str, db: AsyncSession = Depends(get_db)):
    try:
        
        result = await db.execute(select(Companies).filter(Companies.id == id))  
        company = result.scalar_one_or_none()

        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="company not found"
            )

        if company.verified_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="company is already verified"
            )
       
        try:
            company.validate_token(token)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_406_NOT_ACCEPTABLE,
                detail=str(e)
            )

        company.verified_email = True
        company.token = None
        company.token_expires_at = None
        
        await db.commit()
        await db.refresh(company)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "company's email account successfully verified"}
        )

    except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Unexpected error during company registration: {e}."
                )
