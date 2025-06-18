# from fastapi import APIRouter, HTTPException, Depends, status
# from models import Users, UploadTasks
# from sqlalchemy.future import select
# from sqlalchemy.orm import Session
# from database import get_db
# from schemas import TaskCreateRequest
# from fastapi.responses import JSONResponse

# router = APIRouter(
#     prefix="/api/v1",
#     tags=["tasks"]
# )

# @router.post("/upload_task/{user_id}")
# async def upload_task(user_id: str, task_data: TaskCreateRequest, db: Session = Depends(get_db)):
#     try:
#         stmt = select(Users).filter( Users.id == user_id )
#         result = await db.execute(stmt)
#         user = result.scalars().first()

#         if not user:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="User not found",
#             )

#         new_task = UploadTasks(
#             user_id=user_id,
#             platform=task_data.platform,
#             category=task_data.category,
#             type=task_data.type,
#             content=task_data.content,
#             description=task_data.description,
#             engagement=task_data.engagement,
#             amount=task_data.amount,
#             status=task_data.status,
#         )

#         db.add(new_task)
#         await db.commit()

#         task_dict = {
#             "id": str(new_task.id),
#             "user_id": new_task.user_id,
#             "platform": new_task.platform,
#             "category": new_task.category,
#             "type": new_task.type,
#             "content": new_task.content,
#             "description": new_task.description,
#             "status": new_task.status,
#             "created_at": new_task.created_at.isoformat() 
#         }

#         return JSONResponse(
#             status_code=status.HTTP_200_OK,
#             content={"message": "Task uploaded successfully", "task": task_dict}
#         )
#     except Exception as e:
#             raise HTTPException(
#                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#                 detail="Connect to strong network",
#                 headers={"X-Error": str(e)},
#             )
