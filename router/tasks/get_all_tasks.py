# from fastapi import APIRouter, HTTPException, status, Depends
# from sqlalchemy.future import select
# from sqlalchemy.orm import Session
# from database import get_db
# from models import  UploadTasks
# from schemas import UploadTaskResponse
# from fastapi.responses import JSONResponse


# router = APIRouter(
#     prefix="/api/v1",
#     tags=["tasks"]
# )


# @router.get("/tasks", response_model=list[UploadTaskResponse])
# async def get_all_tasks(db: Session = Depends(get_db)):
#     try:
#         stmt = select(UploadTasks)
#         result = await db.execute(stmt)
#         tasks = result.scalars().all()

#         if not tasks:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="No tasks found",
#             )
#         return tasks
    

        

#     except Exception as e:
#         raise HTTPException(
#             status_code=400,
#             detail="Connect to a strong network",
#             headers={"X-Error": str(e)},
#         )
