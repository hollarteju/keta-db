from fastapi import FastAPI
import asyncio
import sys
from database import engine, reset_db, clear_alembic_version, Base
from fastapi.middleware.cors import CORSMiddleware
# from router.tasks import upload_task, get_user_tasks, get_all_tasks, get_task, get_pick_tasks, submit_task, get_submit_tasks
# from router.settings import profile_picture
from dotenv import load_dotenv
import os

from router.auth import register, verify_account
from router.company import get_all_companies

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(register.router)
# app.include_router(login.router)
# app.include_router(resend_code.router)
app.include_router(verify_account.router)
app.include_router(get_all_companies.router)
# app.include_router(get_user_tasks.router)
# app.include_router(get_all_tasks.router)
# app.include_router(get_task.router)
# app.include_router(get_pick_tasks.router)
# app.include_router(submit_task.router)
# app.include_router(get_submit_tasks.router)
# app.include_router(profile_picture.router)

# async def lifespan(app: FastAPI):
#     await reset_db()  # Assuming reset_db is now async
#     yield


# @app.get("/")
# async def read_root():
#     await clear_alembic_version() 
#     await reset_db()  
#     return "Operation completed"
