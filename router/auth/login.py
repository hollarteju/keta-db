from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import User
from schemas import Token, LoginScheme
from database import get_db, create_access_token, create_refresh_token




router = APIRouter(
    prefix="/api/v1",
    tags=["users"]
)


@router.post("/user/login", response_model=Token)
async def login_for_access_token(requests: LoginScheme, db: AsyncSession = Depends(get_db)):
   
    payload = select(User).filter(
        User.email == requests.email
    )

    result = await db.execute(payload)
    user = result.scalars().first()
    
   
    if not user or not user.verify_password(requests.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token_data = {
        "id": str(user.id),  
        "email": user.email,
        "verified_email": user.verified_email,
        "phone_number": user.phone_number,
        "address": user.address,
        "country": user.country,
        "subscription": user.subscription,
        "profile_pic" : user.profile_pic,
        "created_at": user.created_at.isoformat()  
    }

    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data={"id": str(user.id)})

    return Token(
        access_token=access_token, 
        refresh_token=refresh_token,
        token_type="bearer",
        status="success"
        )
