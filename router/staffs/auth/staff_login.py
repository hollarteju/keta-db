# routes/staff.py

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import CompanyStaffs
from schemas import StaffLoginRequest, StaffLoginResponse, StaffVerifyResponse, ResendStaffCode
from database import get_db
from utils.email_config import send_email
from utils.uuid_convert import uuid_to_str, str_to_uuid  # ✅ conversion helper
import random
from datetime import datetime, timedelta
from uuid import UUID
from fastapi.responses import JSONResponse



router = APIRouter(
    prefix="/api/v1/staff",
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

        # send token via email
        await send_email(payload.email, token, "staff_verification")

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
            select(CompanyStaffs).filter(CompanyStaffs.id == uuid_to_str(id))
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
    

@router.post("/resend-verification")
async def resend_verification_email(company: ResendStaffCode, db: AsyncSession = Depends(get_db)):
    
    result = await db.execute(select(CompanyStaffs).filter(CompanyStaffs.email == company.email))
    existing_staff = result.scalar_one_or_none()
    
    if not existing_staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="staff not found"
        )
    
    token = f"{random.randint(0, 9999):04}"
    token_expires_at = datetime.utcnow() + timedelta(minutes=10)

    existing_staff.token = token
    existing_staff.token_expires_at = token_expires_at

    await db.commit()
    await db.refresh(existing_staff)

    
    await send_email(existing_staff.email, str(token), "staff_verification")
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Verification email resent successfully"}
    )
