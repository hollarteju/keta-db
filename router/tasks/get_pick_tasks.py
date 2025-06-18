# from fastapi import APIRouter, HTTPException, status, Depends
# from sqlalchemy.future import select
# from sqlalchemy.orm import Session
# from database import get_db
# from models import PickTasks
# from schemas import PickTaskRespond


# router = APIRouter(
#     prefix="/api/v1",
#     tags=["tasks"]
# )

# @router.get("/user_pick_tasks/{user_id}", response_model=list[PickTaskRespond])
# async def get_pick_tasks(user_id: str, db: Session = Depends(get_db)):
#     try:
#         stmt = select(PickTasks).filter(PickTasks.user_id == user_id)
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

