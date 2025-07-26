import uuid
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from database import Base
from sqlalchemy.sql import func
from passlib.context import CryptContext
from datetime import datetime

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class Companies(Base):
    __tablename__ = "companies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    company_name = Column(String(100), index=True, nullable=True)
    company_industry = Column(String(100), index=True, nullable=True)
    phone_number = Column(String(20), nullable=True, index=True)
    address = Column(String(255), nullable=True, index=True)
    country = Column(String(100), nullable=True, index=True)
    verified_email = Column(Boolean, nullable=True, default=False, index=True)
    subscription = Column(String(50), nullable=True,  index=True)
    profile_pic = Column(String, nullable=True, index=True)
    token = Column(String, unique=True, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), index=True)

    # Relationships
    company_staffs = relationship("CompanyStaffs", back_populates="companies", cascade="all, delete-orphan")

    def verify_password(self, plain_password: str) -> bool:
        return pwd_context.verify(plain_password, self.password)

    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)
    
    def validate_token(self, token: str):
        if self.token != token:
            raise ValueError("Invalid verification token")
        elif self.token_expires_at is None or self.token_expires_at < datetime.utcnow():
            raise ValueError("Verification token has expired")

class CompanyStaffs(Base):
    __tablename__ = "company_staffs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, index=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"))
    full_name = Column(String(100), nullable=False, index=True) 
    email = Column(String(255), unique=True, nullable=False, index=True) 
    password = Column(String(255), nullable=False, index=True)
    phone_number = Column(String(20), nullable=False, index=True)
    job_title = Column(String(100), nullable=False, index=True)
    department = Column(String(100), nullable=False, index=True)  
    profile_pic = Column(String, nullable=True, index=True)
    role = Column(String(100), nullable=False, index=True )
    permissions = Column(JSONB, nullable=False, index=True, default={})
    accept_invitation: bool = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=func.now(), index=True)

    # Relationships
    companies = relationship("Companies", back_populates="company_staffs")
    

# class PickTasks(Base):
#     __tablename__ = "pick_tasks"

#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, index=True)
#     user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
#     task_id = Column(UUID(as_uuid=True), ForeignKey("upload_tasks.id"))
#     uploader_name = Column(String, nullable=False, index=True) 
#     platform = Column(String, nullable=False, index=True) 
#     category = Column(String, nullable=False, index=True)  
#     type = Column(String, nullable=False, index=True)
#     status = Column(String, nullable=False, index=True)
#     created_at = Column(DateTime(timezone=True), default=func.now(), index=True)

#     # Relationships
#     user = relationship("Users", back_populates="pick_tasks")
#     upload_task = relationship("UploadTasks", back_populates="pick_tasks")
#     submit_tasks = relationship("SubmitTasks", back_populates="pick_task")


# class SubmitTasks(Base):
#     __tablename__ = "submit_tasks"

#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, index=True)
#     user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
#     upload_task_id = Column(UUID(as_uuid=True), ForeignKey("upload_tasks.id"))
#     task_id = Column(UUID(as_uuid=True), ForeignKey("pick_tasks.id"))
#     image = Column(String, nullable=False, index=True) 
#     source = Column(String, nullable=True, index=True)  
#     status = Column(String, nullable=False, index=True)
#     created_at = Column(DateTime(timezone=True), default=func.now(), index=True)

#     # Relationships
#     user = relationship("Users", back_populates="submit_tasks")
#     pick_task = relationship("PickTasks", back_populates="submit_tasks")
#     upload_task = relationship("UploadTasks", back_populates="submit_tasks")


# class Notifications(Base):
#     __tablename__ = "notifications"

#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, index=True)
#     user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
#     content = Column(String, nullable=False, index=True)
#     created_at = Column(DateTime(timezone=True), default=func.now(), index=True)

#     # Relationships
#     user = relationship("Users", back_populates="notifications")
