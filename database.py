from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from sqlalchemy import text
from fastapi.security import OAuth2PasswordBearer
from typing import Optional, Annotated
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from fastapi import Depends, FastAPI, HTTPException, status
from datetime import datetime, timedelta, timezone
import jwt
import os
from dotenv import load_dotenv
from schemas import Token, TokenData
import os
from datetime import datetime, timedelta, timezone
from typing import Annotated, Dict
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from jose import jwt, ExpiredSignatureError, JWTError
from schemas import TokenData

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/login")

Base = declarative_base()
metadata = Base.metadata

# Async Engine
engine = create_async_engine(DATABASE_URL, echo=True, future=True)

# AsyncSession
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Function to create an access token
def create_access_token(data: Dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "token_type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Function to create a refresh token
def create_refresh_token(data: Dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "token_type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Dependency to get current user from token
def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("id")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
        return token_data
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        raise credentials_exception

# Function to refresh the access token using the refresh token
async def refresh_access_token(refresh_token: str):
    from models import User
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("id")

        if user_id is None:
            raise credentials_exception

        # 🔍 Load user from database
        async with AsyncSessionLocal() as db:
            query = await db.execute(select(User).where(User.id == user_id))
            user = query.scalars().first()

            if not user:
                raise credentials_exception
            created_at = f"{user.created_at}"
            # ✅ Create new access token with full user info
            access_token = create_access_token(data={
                "id": str(user.id),
                "email": user.email,
                "phone_number": user.phone_number,
                "address" : user.address,
                "country" : user.country,
                "verified_email" : user.verified_email,
                "subscription": user.subscription,
                "profile_pic": user.profile_pic,
                "created_at": created_at.format()

            })

            new_refresh_token = create_refresh_token(data={"id": str(user.id)})

            return {
                "access_token": access_token,
                "refresh_token": new_refresh_token,
                "token_type": "bearer"
            }

    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
# Asynchronous database reset
async def reset_db():
    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all)  # Drop all tables
        await conn.run_sync(Base.metadata.create_all)  # Create tables
    os.system("alembic upgrade head")

# Asynchronous alembic version clear
async def clear_alembic_version():
    async with engine.connect() as connection:
        await connection.execute(text("DELETE FROM alembic_version"))
        print("Alembic version table cleared!")

# Asynchronous database session dependency
async def get_db():
    async with AsyncSessionLocal() as db:
        yield db  # returns db session as an async generator
        await db.commit()  # commits any changes (if applicable)
        await db.close()   # closes the session when done
