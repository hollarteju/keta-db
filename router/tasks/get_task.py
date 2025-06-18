# from fastapi import APIRouter, HTTPException, status, Depends
# from sqlalchemy.future import select
# from sqlalchemy.orm import Session
# from sqlalchemy import func
# from database import get_db
# from models import Users, UploadTasks, PickTasks
# from schemas import UploadTaskResponse, GetTask

# router = APIRouter(
#     prefix="/api/v1",
#     tags=["tasks"]
# )

# @router.post("/get_tasks/{user_id}", response_model=UploadTaskResponse)
# async def get_task_for_user(user_id: str, query: GetTask, db: Session = Depends(get_db)):
#     try:
#         # Fetch user
#         user = await db.execute(select(Users).filter(Users.id == user_id))
#         user = user.scalar_one_or_none()

#         if not user:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="User not found"
#             )

#         # Check if there's a pending task for the user
#         pending_task = await db.execute(
#             select(PickTasks).filter(PickTasks.user_id == user_id, PickTasks.status == 'pending')
#         )
#         pending_task = pending_task.scalars().first()

#         # If there is a pending task, return it
#         if pending_task:
#             task = await db.execute(select(UploadTasks).filter(UploadTasks.id == pending_task.task_id))
#             task = task.scalars().first()
#             if task:
#                 return task  

#         available_task_query = (
#             select(UploadTasks)
#             .filter(UploadTasks.status == 'uploaded', UploadTasks.category == query.category)
#             .filter(UploadTasks.platform == query.platform, UploadTasks.type == query.type)
#             .filter(UploadTasks.user_id != user_id)
#             .filter(UploadTasks.id.notin_(
#                 select(PickTasks.task_id).filter(PickTasks.user_id == user_id)
#             ))
#         )

#         task = await db.execute(available_task_query)
#         task = task.scalar_one_or_none()

#         if not task:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="No available tasks to assign"
#             )

#         uploader = await db.execute(select(Users).filter(Users.id == task.user_id))
#         uploader = uploader.scalar_one_or_none()

#         new_pick_task = PickTasks(
#             user_id=user_id,
#             task_id=task.id,
#             category=task.category,
#             platform=task.platform,
#             type=task.type,
#             status='pending',
#             uploader_name=uploader.full_name,
#             created_at=func.now()
#         )
#         db.add(new_pick_task)
#         db.commit()

#         return task

#     except Exception as e:
#         raise HTTPException(
#             status_code=400,
#             detail="An error occurred while fetching the task.",
#             headers={"X-Error": str(e)}
#         )
