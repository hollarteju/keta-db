# from fastapi import APIRouter, Depends, HTTPException, status
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.future import select
# from models import Companies
# from schemas import Token, LoginScheme
# from database import get_db, create_access_token
# from sqlalchemy.orm import Session




# router = APIRouter(
#     prefix="/api/v1",
#     tags=["users"]
# )


# @router.post("/login", response_model=Token)
# async def login_for_access_token(requests: LoginScheme, db: Session = Depends(get_db)):
   
#     stmt = select(Users).filter(
#         (Users.username == requests.username_or_email) | (Users.email == requests.username_or_email)
#     )
#     result = await db.execute(stmt)
#     user = result.scalars().first()
    
   
#     if not user or not user.verify_password(requests.password):
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid credentials",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
    
#     access_token = create_access_token(data={
#         "sub": str(user.id),  
#         "email": user.email,
#         "username": user.username,
#         "full_name": user.full_name,
#         "verified_email": user.verified_email,
#         "wallet": user.wallet,
#         "account_number": user.account_number,
#         "profile_pic" : user.profile_pic,
#         "created_at": user.created_at.isoformat()  
#     })

#     return Token(access_token=access_token, token_type="bearer")
