from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import Companies
from schemas import Token, LoginScheme
from database import get_db, refresh_access_token


router = APIRouter(
    prefix="/api/v1",
    tags=["token"]
)

@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str, db: AsyncSession = Depends(get_db)):
    new_token = await refresh_access_token(refresh_token)
    return Token(
        access_token=new_token["access_token"],
        refresh_token=refresh_token,
        token_type="bearer",
        status="success"
    )