# from fastapi import APIRouter, HTTPException, status, Depends
# from sqlalchemy.future import select
# from sqlalchemy.orm import Session
# from database import get_db
# from models import SubmitTasks
# from schemas import PickTaskRespond


# router = APIRouter(
#     prefix="/api/v1",
#     tags=["tasks"]
# )

# @router.get("/get_submitted_task/{task_id}", response_model=list[PickTaskRespond])
# async def get_submitted_tasks(task_id: str, db: Session = Depends(get_db)):
#     try:
#         stmt = select(SubmitTasks).filter(SubmitTasks.task_id == task_id)
#         result = await db.execute(stmt)
#         tasks = result.scalars().all()

#         if not tasks:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="No submitted tasks found for this user",
#             )

#         return tasks

#     except Exception as e:
#         raise HTTPException(
#             status_code=400,
#             detail="Connect to strong network",
#             headers={"X-Error": str(e)},
#         )

