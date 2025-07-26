from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from schemas import StaffCreate, StaffAccept, StaffPermissionUpdate, StaffDelete 
from fastapi.responses import JSONResponse
from models import Companies, CompanyStaffs
import uuid
from typing import Dict
from utils.email_config import send_email


router = APIRouter(
    prefix="/api/v1",
    tags=["companies"]
)

@router.post("/onboarding/staff", status_code=status.HTTP_201_CREATED)
async def create_staff(staff: StaffCreate, db: AsyncSession = Depends(get_db)):
    try:
        company_id= staff.company_id
        company = await db.execute(select(Companies).filter(Companies.id == company_id))
        check =  company.scalar_one_or_none()
        if not check:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

        hashed_password = Companies.hash_password(staff.password)
        db_staff = CompanyStaffs(
            company_id=company_id,
            full_name=staff.full_name,
            email=staff.email,
            password=hashed_password,
            phone_number=staff.phone_number,
            job_title=staff.job_title,
            department=staff.department,
            role=staff.role,
            permissions=staff.permissions.dict(),
        )

        db.add(db_staff)
        await db.commit()
        await db.refresh(db_staff)

        redirect = f"https://tracc-box.vercel.app/onboarding?company={company_id}&&onboard_staff={staff.email}"
        await send_email(staff.email, redirect, "onboarding.html" )

        return {
            "status": "success",
            "message": "Company updated successfully",
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during company registration: {e}."
        )

@router.post("/onboarding/staff/accept", status_code=status.HTTP_200_OK)
async def accept_invitation(staff: StaffAccept, db: AsyncSession = Depends(get_db)):
    query = select(CompanyStaffs).filter(
        CompanyStaffs.company_id == staff.company_id,
        CompanyStaffs.email == staff.email
    )

    result = await db.execute(query)
    staff = result.scalar_one_or_none()

    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    if staff.accept_invitation:
        return JSONResponse(
            status_code=200,
            content={"message": "Invitation already accepted"}
        )

    staff.accept_invitation = True
    db.add(staff)
    await db.commit()
    await db.refresh(staff)

    return {
            "message": "Invitation accepted successfully", 
            "staff": {
            "id": str(staff.id),
            "full_name": staff.full_name,
            "email": staff.email,
            "accept_invitation": staff.accept_invitation
        }}



@router.patch("/onboarding/staff/permissions")
async def update_permissions(staff: StaffPermissionUpdate, status_code=status.HTTP_201_CREATED, db: AsyncSession = Depends(get_db)):
    company_id = staff.company_id
    query = select(CompanyStaffs).filter(
        CompanyStaffs.id == staff.staff_id,
        CompanyStaffs.company_id == company_id
    )

    result = await db.execute(query)
    company = result.scalar_one_or_none()

    if not company:
        raise HTTPException(status_code=404, detail="Staff not found")
    
    company.permissions = staff.permissions
    await db.commit()
    await db.refresh(staff)

    return query


@router.delete("/onboarding/staff/permissions")
async def update_permissions(staff: StaffDelete, db: AsyncSession = Depends(get_db)):
    query = select(CompanyStaffs).filter(
        CompanyStaffs.id == staff.staff_id,
        CompanyStaffs.company_id == staff.company_id
    )

    result = await db.execute(query)
    staff = result.scalar_one_or_none()

    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    
    await db.delete()
    await db.commit()

    remaining_query = select(CompanyStaffs).filter(
        CompanyStaffs.company_id == staff.company_id
    )
    remaining_result = await db.execute(remaining_query)
    remaining_staffs = remaining_result.scalars().all()

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        data = remaining_staffs,
        content={"message": "staff permission updated successfully"}
    )