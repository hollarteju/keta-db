from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import Users
from schemas import profilePicture, profilePictureResponse
from database import get_db

router = APIRouter(
    prefix="/api/v1",
    tags=["settings"]
)

@router.post("/profile_picture/{user_id}", response_model=profilePictureResponse)
async def upload_profile_picture(user_id: str, image: profilePicture, db: AsyncSession = Depends(get_db)):
    try:
        # Fetch the user asynchronously
        result = await db.execute(select(Users).filter(Users.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Update the user's profile picture URL
        user.profile_pic = image.image_url
        
        # Commit the transaction asynchronously
        await db.commit()

        return profilePictureResponse(
            image_url=image.image_url,
        )

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail="An error occurred while uploading the profile picture.",
            headers={"X-Error": str(e)}
        )





# from fastapi import APIRouter, HTTPException, status, Depends
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.future import select
# from models import SubmitTasks, PickTasks, Users
# from schemas import profilePicture, profilePictureResponse
# from database import get_db
# from schemas import profilePicture, profilePictureResponse

# router = APIRouter(
#     prefix="/api/v1",
#     tags=["settings"]
# )

# @router.post("/profile_picture/{user_id}", response_model=profilePictureResponse)
# async def upload_profile_picture(user_id: str, image: profilePicture, db: AsyncSession = Depends(get_db)):
#     try:
#         # Use AsyncSession and await execute
#         result = await db.execute(select(Users).filter(Users.id == user_id))
#         user = result.scalars().first()
        
#         if not user:
#             raise HTTPException(status_code=404, detail="User not found")
        
#         # Update the user's profile picture URL
#         user.profile_pic = image.image_url

#         # Commit the transaction asynchronously
#         await db.commit()

#         return profilePictureResponse(
#             image_url=image.image_url,
#         )

#     except Exception as e:
#         raise HTTPException(
#             status_code=400,
#             detail="An error occurred while uploading the profile picture.",
#             headers={"X-Error": str(e)}
#         )
