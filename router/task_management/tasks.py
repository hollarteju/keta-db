from uuid import UUID
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models import Tasks, Companies, CompanyStaffs
from schemas import TaskCreate, TaskResponse, TaskStatus, EditTask
from utils.uuid_convert import uuid_to_str, str_to_uuid
from sqlalchemy.orm import selectinload



router = APIRouter(
    prefix="/api/v1/tasks",
    tags=["tasks"]
)


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(task: TaskCreate, db: AsyncSession = Depends(get_db)):
    try:
        # ✅ Validate company if provided
        if task.company_id:
            result = await db.execute(
                select(Companies).filter(Companies.id == uuid_to_str(task.company_id))
            )
            company = result.scalar_one_or_none()
            if not company:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Company not found"
                )

        # ✅ Validate staff if provided
        if task.staff_id:
            result = await db.execute(
                select(CompanyStaffs).filter(CompanyStaffs.id == uuid_to_str(task.staff_id))
            )
            staff = result.scalar_one_or_none()
            if not staff:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Staff not found"
                )

        # ✅ Create Task record
        db_task = Tasks(
            company_id=uuid_to_str(task.company_id) if task.company_id else None,
            staff_id=uuid_to_str(task.staff_id) if task.staff_id else None,
            task_title=task.task_title,
            task_type=task.task_type,
            customer_name=task.customer_name,
            customer_phone=task.customer_phone,
            description=task.description,
            location=task.location,
            date=task.date,
            time=task.time,
            priority=task.priority,
            attachment=[a.model_dump() for a in task.attachment] if task.attachment else None,
            status=task.status or TaskStatus.pending

        )

        db.add(db_task)
        await db.commit()
        await db.refresh(db_task)

        return db_task

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during task creation: {e}"
        )
    


@router.get("/company/{company_id}", status_code=status.HTTP_200_OK)
async def get_company_tasks(company_id: UUID, db: AsyncSession = Depends(get_db)):
    try:
        query = (
            select(Tasks)
            .options(selectinload(Tasks.staff))
            .filter(Tasks.company_id == uuid_to_str(company_id))
            .order_by(Tasks.created_at.desc())
        )
        result = await db.execute(query)
        tasks = result.scalars().all()

        if not tasks:
            raise HTTPException(status_code=404, detail="No tasks found for this company")

        # Build custom response with staff info
        response = []
        for task in tasks:
            response.append({
                "id": task.id,
                "task_title": task.task_title,
                "task_type": task.task_type,
                "customer_name": task.customer_name,
                "customer_phone": task.customer_phone,
                "description": task.description,
                "location": task.location,
                "date": task.date,
                "time": task.time,
                "priority": task.priority.value if task.priority else None,
                "attachment": task.attachment,
                "status": task.status,
                "staff_id": task.staff.id if task.staff else None,
                "staff_name": task.staff.full_name if task.staff else None,
                "created_at": task.created_at
            })
        return {"status": "success", "total": len(response), "tasks": response}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching company tasks: {e}")



@router.patch("/{company_id}/{staff_id}/{task_id}")
async def update_task(
    company_id: str,
    staff_id: str,
    task_id: str,
    task_data: EditTask,
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await db.execute(
            select(Tasks).filter(
                Tasks.id == task_id,
                Tasks.company_id == uuid_to_str(company_id),
                Tasks.staff_id == uuid_to_str(staff_id)
            )
        )
        db_task = result.scalar_one_or_none()

        if not db_task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Update fields dynamically
        for key, value in task_data.model_dump(exclude_unset=True).items():
            setattr(db_task, key, value)

        await db.commit()
        await db.refresh(db_task)

        return {"status": "success", "message": "Task updated successfully"}

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update task: {e}")


# 🟥 DELETE TASK — filter by company_id and staff_id
@router.delete("/{company_id}/{staff_id}/{task_id}")
async def delete_task(company_id: str, staff_id: str, task_id: str, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(
            select(Tasks).filter(
                Tasks.id == task_id,
                Tasks.company_id == uuid_to_str(company_id),
                Tasks.staff_id == uuid_to_str(staff_id)
            )
        )
        db_task = result.scalar_one_or_none()

        if not db_task:
            raise HTTPException(status_code=404, detail="Task not found")

        await db.delete(db_task)
        await db.commit()

        return {"status": "success", "message": "Task deleted successfully"}

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete task: {e}")


@router.patch("/{company_id}/{staff_id}/{task_id}/status")
async def change_task_status(
    company_id: str,
    staff_id: str,
    task_id: str,
    payload: dict,  # expects { "status": "completed" }
    db: AsyncSession = Depends(get_db)
):
    try:
        # ✅ Validate status input
        new_status = payload.get("status")
        allowed_status = ["pending", "completed", "overdue"]

        if not new_status or new_status not in allowed_status:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of {allowed_status}"
            )

        # ✅ Validate staff exists and belongs to company
        staff_result = await db.execute(
            select(CompanyStaffs).filter(
                CompanyStaffs.id == uuid_to_str(staff_id),
                CompanyStaffs.company_id == uuid_to_str(company_id)
            )
        )
        staff = staff_result.scalar_one_or_none()
        if not staff:
            raise HTTPException(status_code=404, detail="Staff not found or not in company")

        # ✅ Find the task owned by that staff and company
        result = await db.execute(
            select(Tasks).filter(
                Tasks.id == task_id,
                Tasks.company_id == uuid_to_str(company_id),
                Tasks.staff_id == uuid_to_str(staff_id)
            )
        )
        db_task = result.scalar_one_or_none()
        if not db_task:
            raise HTTPException(status_code=404, detail="Task not found for this staff")

        # ✅ Update only the status
        db_task.status = new_status

        await db.commit()
        await db.refresh(db_task)

        return {
            "status": "success",
            "message": f"Task status updated to '{new_status}'",
            "task": {
                "id": db_task.id,
                "task_title": db_task.task_title,
                "status": db_task.status
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update task status: {e}"
        )
    

@router.get("/{company_id}/{staff_id}/my-tasks")
async def get_staff_tasks(company_id: str, staff_id: str, db: AsyncSession = Depends(get_db)):
    try:
        # ✅ Validate staff existence under the company
        staff_result = await db.execute(
            select(CompanyStaffs).filter(
                CompanyStaffs.id == uuid_to_str(staff_id),
                CompanyStaffs.company_id == uuid_to_str(company_id)
            )
        )
        staff = staff_result.scalar_one_or_none()
        if not staff:
            raise HTTPException(status_code=404, detail="Staff not found or does not belong to this company")

        # ✅ Fetch tasks assigned to this staff
        task_result = await db.execute(
            select(Tasks)
            .filter(
                Tasks.company_id == uuid_to_str(company_id),
                Tasks.staff_id == uuid_to_str(staff_id)
            )
            .order_by(Tasks.date.desc(), Tasks.time.desc())
        )

        tasks = task_result.scalars().all()

        if not tasks:
            return {
                "status": "success",
                "message": "No tasks assigned yet",
                "tasks": []
            }

        return {
            "status": "success",
            "total": len(tasks),
            "staff": {
                "id": staff.id,
                "name": staff.full_name,
                "job_title": staff.job_title
            },
            "tasks": [
                {
                    "id": t.id,
                    "task_title": t.task_title,
                    "task_type": t.task_type,
                    "customer_name": t.customer_name,
                    "customer_phone": t.customer_phone,
                    "description": t.description,
                    "location": t.location,
                    "date": t.date,
                    "time": t.time,
                    "priority": t.priority,
                    "attachment": t.attachment,
                    "status": t.status
                }
                for t in tasks
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve tasks: {e}"
        )