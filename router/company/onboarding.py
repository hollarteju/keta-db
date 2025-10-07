from uuid import UUID
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi.responses import JSONResponse

from database import get_db
from schemas import (
    StaffCreate, StaffAccept, StaffPermissionUpdate, StaffDelete,
    StaffResponse, AttendanceRecordResponse
)
from models import Companies, CompanyStaffs
from utils.uuid_convert import str_to_uuid, uuid_to_str
from utils.email_config import send_email

from datetime import date


router = APIRouter(
    prefix="/api/v1",
    tags=["companies"]
)


@router.post("/onboarding/staff", status_code=status.HTTP_201_CREATED)
async def create_staff(staff: StaffCreate, db: AsyncSession = Depends(get_db)):
    try:
        # ✅ Convert UUID → str for query
        company = await db.execute(
            select(Companies).filter(Companies.id == uuid_to_str(staff.company_id))
        )
        check = company.scalar_one_or_none()
        if not check:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

        hashed_password = Companies.hash_password(staff.password)
        db_staff = CompanyStaffs(
            company_id=uuid_to_str(staff.company_id),
            full_name=staff.full_name,
            email=staff.email,
            password=hashed_password,
            phone_number=staff.phone_number,
            job_title=staff.job_title,
            department=staff.department,
            role=staff.role,
            permissions=staff.permissions.model_dump(),
        )

        db.add(db_staff)
        await db.commit()
        await db.refresh(db_staff)

        redirect = f"https://tracc-box.vercel.app/accept-invitation?company_id={staff.company_id}&email={staff.email}"
        msg = await send_email(staff.email, redirect, "onboarding_verification")
        print(f"verification text..... {msg}")
        return {
            "status": "success",
            "message": "Staff created successfully",
            "staff_id": str_to_uuid(db_staff.id)  # ✅ return UUID
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during staff creation: {e}."
        )


@router.post("/onboarding/staff/accept", status_code=status.HTTP_200_OK)
async def accept_invitation(staff: StaffAccept, db: AsyncSession = Depends(get_db)):
    query = select(CompanyStaffs).filter(
        CompanyStaffs.company_id == uuid_to_str(staff.company_id),
        CompanyStaffs.email == staff.email
    )

    result = await db.execute(query)
    db_staff = result.scalar_one_or_none()

    if not db_staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    if db_staff.accept_invitation:
        return JSONResponse(
            status_code=200,
            content={"message": "Invitation already accepted"}
        )

    db_staff.accept_invitation = True
    db.add(db_staff)
    await db.commit()
    await db.refresh(db_staff)

    return {
        "message": "Invitation accepted successfully",
        "staff": {
            "id": str_to_uuid(db_staff.id),   # ✅ convert to UUID
            "full_name": db_staff.full_name,
            "email": db_staff.email,
            "role": db_staff.role,
            "accept_invitation": db_staff.accept_invitation
        }
    }


@router.patch("/onboarding/staff/permissions")
async def update_permissions(staff: StaffPermissionUpdate, db: AsyncSession = Depends(get_db)):
    query = select(CompanyStaffs).filter(
        CompanyStaffs.id == uuid_to_str(staff.staff_id),
        CompanyStaffs.company_id == uuid_to_str(staff.company_id)
    )

    result = await db.execute(query)
    db_staff = result.scalar_one_or_none()

    if not db_staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    db_staff.permissions = staff.permissions.dict()
    await db.commit()
    await db.refresh(db_staff)

    return {
        "status": "success",
        "staff_id": str_to_uuid(db_staff.id),
        "updated_permissions": db_staff.permissions
    }


@router.delete("/onboarding/staff/permissions")
async def delete_staff(staff: StaffDelete, db: AsyncSession = Depends(get_db)):
    query = select(CompanyStaffs).filter(
        CompanyStaffs.id == uuid_to_str(staff.staff_id),
        CompanyStaffs.company_id == uuid_to_str(staff.company_id)
    )

    result = await db.execute(query)
    db_staff = result.scalar_one_or_none()

    if not db_staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    await db.delete(db_staff)
    await db.commit()

    remaining_query = select(CompanyStaffs).filter(
        CompanyStaffs.company_id == uuid_to_str(staff.company_id)
    )
    remaining_result = await db.execute(remaining_query)
    remaining_staffs = remaining_result.scalars().all()

    return {
        "status": "success",
        "message": "Staff deleted successfully",
        "remaining_staffs": [
            {
                "id": str_to_uuid(s.id),
                "full_name": s.full_name,
                "email": s.email,
                "role": s.role
            } for s in remaining_staffs
        ]
    }

@router.get("/{company_id}/all_staffs", response_model=list[StaffResponse])
async def get_company_staffs(company_id: UUID, db: AsyncSession = Depends(get_db)):
    try:
        query = (
            select(CompanyStaffs)
            .options(selectinload(CompanyStaffs.attendance_records))
            .where(CompanyStaffs.company_id == str(company_id))
        )

        result = await db.execute(query)
        staffs = result.scalars().all()

        today = date.today()
        staff_responses = []

        for s in staffs:
            # find today's attendance record
            today_record = next(
                (record for record in s.attendance_records if record.attendance_date == today),
                None,
            )

            # Construct StaffResponse with all required fields
            staff_obj = StaffResponse(
                id=s.id,
                full_name=getattr(s, "full_name", "Unknown"),
                email=getattr(s, "email", None),
                profile_pic=getattr(s, "profile_pic", None),
                phone_number=getattr(s, "phone_number", None),
                job_title=getattr(s, "job_title", None),
                department=getattr(s, "department", None),
                role=getattr(s, "role", None),
                accept_invitation=getattr(s, "accept_invitation", None),
                is_active=getattr(s, "is_active", False),
                created_at=getattr(s, "created_at", date.today()),  # fallback if missing
                attendance_records=[
                    AttendanceRecordResponse(
                        id=today_record.id,
                        attendance_date=today_record.attendance_date,
                        check_in_time=getattr(today_record, "check_in_time", None),
                        check_out_time=getattr(today_record, "check_out_time", None),
                        created_at=getattr(today_record, "created_at", date.today()),
                        updated_at=getattr(today_record, "updated_at", date.today()),
                    )
                ] if today_record else []
            )

            staff_responses.append(staff_obj)

        return staff_responses

    except Exception as e:
        # Don't put exception text in headers (avoids "Invalid HTTP header" issue)
        print(f"Error retrieving staff: {e}")  # log for debugging
        raise HTTPException(
            status_code=400,
            detail="Error retrieving staff. Please check your connection."
        )