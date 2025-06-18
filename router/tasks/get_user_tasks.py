# from fastapi import APIRouter, HTTPException, status, Depends
# from sqlalchemy.future import select
# from sqlalchemy.orm import Session
# from database import get_db
# from models import Users, UploadTasks
# from schemas import UploadTaskResponse
# from fastapi.responses import JSONResponse


# router = APIRouter(
#     prefix="/api/v1",
#     tags=["tasks"]
# )

# @router.get("/user_tasks/{user_id}", response_model=list[UploadTaskResponse])
# async def get_user_tasks(user_id: str, db: Session = Depends(get_db)):
#     try:
#         stmt = select(UploadTasks).filter(UploadTasks.user_id == user_id)
#         result = await db.execute(stmt)
#         tasks = result.scalars().all()

#         if not tasks:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="No tasks found for this user",
#             )

#         return tasks

#     except Exception as e:
#         raise HTTPException(
#             status_code=400,
#             detail="Connect to strong network",
#             headers={"X-Error": str(e)},
#         )

