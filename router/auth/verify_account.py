from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from models import User
from database import get_db
from sqlalchemy.future import select
from uuid import UUID
from fastapi.responses import JSONResponse
from utils.uuid_convert import uuid_to_str, str_to_uuid


router = APIRouter(
    prefix="/api/v1",
    tags=["users"]
)

@router.post("/user/verify_email")
async def verify_account(id: UUID, token:str, db: AsyncSession = Depends(get_db)):
    try:
        
        result = await db.execute(select(User).filter(User.id == uuid_to_str(id)))  
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="user not found"
            )

        if user.verified_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="user is already verified"
            )
       
        try:
            user.validate_token(token)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_406_NOT_ACCEPTABLE,
                detail=str(e)
            )

        user.verified_email = True
        user.token = None
        user.token_expires_at = None
        
        await db.commit()
        await db.refresh(user)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "user's email account successfully verified"}
        )

    except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Unexpected error during user registration: {e}."
                )
