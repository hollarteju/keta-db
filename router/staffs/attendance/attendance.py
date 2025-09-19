from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, date
import uuid

from database import get_db
from models import AttendanceRecord
from schemas import AttendanceCheckInRequest, AttendanceCheckOutRequest, AttendanceResponse

router = APIRouter(
    prefix="/api/v1/attendance",
    tags=["attendance"]
)

# --------------------
# Staff Check-in
# --------------------
@router.post("/check-in", response_model=AttendanceResponse)
async def check_in(data: AttendanceCheckInRequest, db: AsyncSession = Depends(get_db)):
    try:
        today = date.today()

        # Check if staff already checked in today
        query = select(AttendanceRecord).where(
            AttendanceRecord.staff_id == data.staff_id,
            AttendanceRecord.company_id == data.company_id,
            AttendanceRecord.attendance_date == today
        )
        result = await db.execute(query)
        record = result.scalars().first()

        if record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Staff already checked in today"
            )

        new_record = AttendanceRecord(
            staff_id=data.staff_id,
            company_id=data.company_id,
            attendance_date=today,
            check_in_time=datetime.utcnow()
        )

        db.add(new_record)
        await db.commit()
        await db.refresh(new_record)

        return new_record

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# --------------------
# Staff Check-out
# --------------------
@router.post("/check-out", response_model=AttendanceResponse)
async def check_out(data: AttendanceCheckOutRequest, db: AsyncSession = Depends(get_db)):
    try:
        today = date.today()

        # Find today's attendance record
        query = select(AttendanceRecord).where(
            AttendanceRecord.staff_id == data.staff_id,
            AttendanceRecord.company_id == data.company_id,
            AttendanceRecord.attendance_date == today
        )
        result = await db.execute(query)
        record = result.scalars().first()

        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No check-in record found for today"
            )

        if record.check_out_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Staff already checked out today"
            )

        record.check_out_time = datetime.utcnow()
        await db.commit()
        await db.refresh(record)

        return record

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/status/{staff_id}")
async def get_attendance_status(staff_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    today = date.today()

    query = select(AttendanceRecord).where(
        AttendanceRecord.staff_id == staff_id,
        AttendanceRecord.attendance_date == today
    )
    result = await db.execute(query)
    record = result.scalars().first()

    if not record:
        return {"status": "NOT_CHECKED_IN"}

    if record.check_in_time and not record.check_out_time:
        return {"status": "CHECKED_IN", "check_in_time": record.check_in_time}

    if record.check_in_time and record.check_out_time:
        return {"status": "CHECKED_OUT", "check_in_time": record.check_in_time, "check_out_time": record.check_out_time}
