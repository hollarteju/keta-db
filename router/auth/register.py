from sqlalchemy.future import select
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from models import User
from schemas import CreateUser, UserResponse, RegisterUserResponse
from utils.email_config import send_email
import random
from datetime import datetime, timedelta
from schemas import Token
from database import get_db, create_access_token, create_refresh_token




router = APIRouter(
    prefix="/api/v1",
    tags=["users"]
)

@router.post("/user/register", response_model=Token)
async def create_user(user: CreateUser, db: AsyncSession = Depends(get_db)):
    # try:
        result = await db.execute(select(User).filter(User.email == user.email))
        existing_user_email =  result.scalar_one_or_none()
        
        if existing_user_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="email already taken by another user"
            )
        
        if not User.is_valid_password(user.password):
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="invalid password format"
            )
        
        hashed_password = User.hash_password(user.password)

        token = f"{random.randrange(10**5):05}"
        token_expires_at = datetime.utcnow() + timedelta(minutes=10)


        new_user = User(
            full_name = user.full_name,
            email=user.email,
            password=hashed_password,  
            token = token,
            token_expires_at=token_expires_at
        )

        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        access_token = create_access_token(data={"sub": str(new_user.id)})
        refresh_token = create_refresh_token(data={"sub": str(new_user.id)})

        try:
          await  send_email(user.email, str(token), "keta-sign-up")
        
        except Exception:
             raise HTTPException(
                  status_code= status.HTTP_503_SERVICE_UNAVAILABL,
                  detail="Verification email could not be sent. Please try again."
             )
        return Token(
        access_token=access_token, 
        refresh_token=refresh_token,
        token_type="bearer",
        status="success"
        )

    # except Exception as e:
    #         raise HTTPException(
    #             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    #             detail=f"Unexpected error during company registration: {e}."
    #         )
