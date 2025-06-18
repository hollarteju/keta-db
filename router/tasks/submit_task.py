# from fastapi import APIRouter, HTTPException, status, Depends
# from sqlalchemy.orm import Session
# from sqlalchemy.future import select
# from models import SubmitTasks, PickTasks, Users
# from schemas import SubmitTaskRequest, SubmitTaskResponse
# from database import get_db
# from uuid import UUID

# router = APIRouter(
#     prefix="/api/v1",
#     tags=["tasks"]
# )

# @router.post("/submit_task/{user_id}", response_model=SubmitTaskResponse)
# async def submit_task(user_id: UUID, task_data: SubmitTaskRequest, db: Session = Depends(get_db)):
#     try:
      
#         user = await db.execute(select(Users).filter(Users.id == user_id))
#         user = user.scalar_one_or_none()
        
#         if not user:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="User not found"
#             )
        
#         pick_task = await db.execute(
#             select(PickTasks).filter(PickTasks.user_id == user_id, PickTasks.task_id == task_data.task_id)
#         )

#         pick_task = pick_task.scalars().first() 

#         if not pick_task:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="Pick task not found or does not belong to this user"
#             )

#         if pick_task.status != "pending":
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Task is not in a pending state"
#             )

#         submit_task = SubmitTasks(
#             user_id=user_id,
#             task_id=pick_task.id,
#             image=task_data.image,
#             source=task_data.source,
#             status="submitted",
#         )

#         db.add(submit_task)

#         pick_task.status = "submitted"

#         db.commit()

#         pick_task.status = "submitted"
#         db.commit()

#         return SubmitTaskResponse(
#             status=submit_task.status,
#         )

#     except Exception as e:
#         raise HTTPException(
#             status_code=400,
#             detail="An error occurred while submitting the task.",
#             headers={"X-Error": str(e)}
#         )
