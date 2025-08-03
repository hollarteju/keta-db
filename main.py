from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# from router.tasks import upload_task, get_user_tasks, get_all_tasks, get_task, get_pick_tasks, submit_task, get_submit_tasks
# from router.settings import profile_picture
from dotenv import load_dotenv
import os

from router.auth import register, verify_account, login, resend_code, forgotten_password, update_company
from router.company import get_all_companies, onboarding
from router.staffs.auth import staff_login 
from router.refresh_token import refresh_token

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
app.include_router(login.router)
app.include_router(staff_login.router)
app.include_router(resend_code.router)
app.include_router(verify_account.router)
app.include_router(get_all_companies.router)
app.include_router(forgotten_password.router)
app.include_router(update_company.router)
app.include_router(refresh_token.router)
app.include_router(onboarding.router)
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
