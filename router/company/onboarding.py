from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from schemas import StaffCreate, StaffAccept, StaffPermissionUpdate, StaffDelete, StaffResponse, AttendanceRecordResponse
from fastapi.responses import JSONResponse
from models import Companies, CompanyStaffs
from sqlalchemy.orm import selectinload

import uuid
from typing import Dict
from utils.email_config import send_email
from datetime import date


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

        redirect = f"https://tracc-box.vercel.app/accept-invitation?company_id={company_id}&email={staff.email}"
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
            "role": staff.role,
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


@router.get("/{company_id}/all_staffs", response_model=list[StaffResponse])
async def get_company_staffs(company_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    try:
        query = select(CompanyStaffs).options(selectinload(CompanyStaffs.attendance_records)).where(CompanyStaffs.company_id == company_id)
        result = await db.execute(query)
        staffs = result.scalars().all()

        today = date.today()

        # Transform staff.attendance_records → today_attendance
        staff_responses = []
        for staff in staffs:
            today_record = next(
                (record for record in staff.attendance_records if record.attendance_date == today),
                None
            )

            staff_obj = StaffResponse.model_validate(staff)  # ✅ new Pydantic v2 method
            if today_record:
                staff_obj.today_attendance = AttendanceRecordResponse.model_validate(today_record)

            staff_responses.append(staff_obj)

        if not staff_responses:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No staffs found for this company",
            )

        return staff_responses


    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail="Error retrieving staff. Please check your connection.",
            headers={"X-Error": str(e)},
        )
