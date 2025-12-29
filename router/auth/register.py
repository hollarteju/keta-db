from sqlalchemy.future import select
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from models import User
from schemas import CreateUser, UserResponse, RegisterUserResponse
from database import get_db
from utils.email_config import send_email
import random
from datetime import datetime, timedelta




router = APIRouter(
    prefix="/api/v1",
    tags=["users"]
)

@router.post("/user/register", response_model=RegisterUserResponse)
async def create_user(user: CreateUser, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(User).filter(User.email == user.email))
        existing_user_email =  result.scalar_one_or_none()
        
        if existing_user_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="email already taken by another user"
            )
        
        hashed_password = User.hash_password(user.password)

        token = f"{random.randint(0, 9999):04}"
        token_expires_at = datetime.utcnow() + timedelta(minutes=10)


        new_company = User(
            email=user.email,
            password=hashed_password,  
            token = token,
            token_expires_at=token_expires_at
        )

        db.add(new_company)
        await db.commit()
        await db.refresh(new_company)
        try:
          await  send_email(user.email, str(token), "user_verification")
        
        except Exception as e:
             raise HTTPException(
                  status_code= status.HTTP_404_NOT_FOUND,
                  detail=f"email not sent: {e}"
             )
        return RegisterUserResponse(
            status="success",
            message="user registered successfully",
            company=UserResponse.model_validate(new_company)
        )

    except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unexpected error during company registration: {e}."
            )
