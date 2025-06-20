from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import Companies
from schemas import Token, LoginScheme
from database import get_db, create_access_token




router = APIRouter(
    prefix="/api/v1",
    tags=["companies"]
)


@router.post("/login", response_model=Token)
async def login_for_access_token(requests: LoginScheme, db: AsyncSession = Depends(get_db)):
   
    payload = select(Companies).filter(
        (Companies.email == requests.email) | (Companies.email == requests.email)
    )

    result = await db.execute(payload)
    company = result.scalars().first()
    
   
    if not company or not company.verify_password(requests.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={
        "id": str(company.id),  
        "email": company.email,
        "company_name": company.company_name,
        "company_industry": company.company_industry,
        "verified_email": company.verified_email,
        "phone_number": company.phone_number,
        "address": company.address,
        "country": company.country,
        "subscription": company.subscription,
        "profile_pic" : company.profile_pic,
        "created_at": company.created_at.isoformat()  
    })

    return Token(
        access_token=access_token, 
        token_type="bearer",
        status="success"
        )
