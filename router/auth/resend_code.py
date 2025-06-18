from sqlalchemy.future import select
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from models import Users
from schemas import CreateUser
from database import get_db
from utils.email_config import send_email


router = APIRouter(
    prefix="/api/v1",
    tags=["users"]
)

@router.post("/resend-verification")
async def resend_verification_email(user: CreateUser, db: Session = Depends(get_db)):

    # Check if the user exists by email
    result = await db.execute(select(Users).filter(Users.email == user.email))
    existing_user = result.scalar_one_or_none()

    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check if verification email has already been sent
    if existing_user.verified_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your account has been verified"
        )
    
    # Send verification email again
    await send_email(existing_user.email, existing_user.full_name, str(existing_user.id))
   
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": "Verification email resent successfully"}
    )