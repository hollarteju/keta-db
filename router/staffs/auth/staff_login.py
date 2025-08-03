# routes/staff.py

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import CompanyStaffs
from schemas import StaffLoginRequest, StaffLoginResponse, StaffVerifyResponse
from database import get_db
from utils.email_config import send_email
import random
from datetime import datetime, timedelta
from uuid import UUID

router = APIRouter(
    prefix="/api/v1",
    tags=["staff"]
)

@router.post("/login", response_model=StaffLoginResponse)
async def staff_login(payload: StaffLoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(
            select(CompanyStaffs).filter(CompanyStaffs.email == payload.email)
        )
        staff = result.scalar_one_or_none()
        
        if not staff:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Staff not found"
            )
        
        # Generate and assign token
        token = f"{random.randint(0, 9999):04}"
        staff.token = token
        staff.token_expires_at = datetime.utcnow() + timedelta(minutes=10)

        await db.commit()
        await db.refresh(staff)

        await send_email(payload.email, token, "verify_staff.html")

        return StaffLoginResponse(id=staff.id)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during staff login: {e}."
        )

@router.post("/verify_email", response_model=StaffVerifyResponse)
async def verify_account(id: UUID, token: str, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(
            select(CompanyStaffs).filter(CompanyStaffs.id == id)
        )
        staff = result.scalar_one_or_none()

        if not staff:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Staff not found"
            )

        try:
            staff.validate_token(token)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_406_NOT_ACCEPTABLE,
                detail=str(e)
            )

        # Invalidate token after successful verification
        staff.token = None
        staff.token_expires_at = None

        await db.commit()
        await db.refresh(staff)

        return StaffVerifyResponse(
            id=staff.id,
            full_name=staff.full_name,
            email=staff.email,
            phone_number=staff.phone_number,
            job_title=staff.job_title,
            department=staff.department,
            profile_pic=staff.profile_pic,
            role=staff.role,
            permissions=staff.permissions,
            accept_invitation=staff.accept_invitation,
            created_at=staff.created_at,
            company_id=staff.company_id,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during verification: {e}."
        )
