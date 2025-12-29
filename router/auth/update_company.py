from uuid import UUID
from sqlalchemy import update
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.future import select
from models import User
from schemas import UpdateUserResponse, UpdateUser
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from utils.uuid_convert import uuid_to_str, str_to_uuid


router = APIRouter(
    prefix="/api/v1",
    tags=["users"]
)

@router.put("/update/{user_id}")
async def update_user(user_id: UUID, user_data: UpdateUser, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(User).where(User.id == uuid_to_str(user_id)))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="user not found"
            )
        

        if not user.verified_email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email not verified. Please verify your email before updating your user details."
            )

        for field, value in user_data.model_dump(exclude_unset=True).items():
            setattr(user, field, value)


        await db.commit()
        await db.refresh(user)

        return {
            "status": "success",
            "message": "user updated successfully",
            "user": user
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user: {e}"
        )
