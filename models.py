import uuid
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base
from sqlalchemy.sql import func
from passlib.context import CryptContext
from datetime import datetime

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class Companies(Base):
    __tablename__ = "companies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    company_name = Column(String, index=True, nullable=True)
    company_industry = Column(String, index=True, nullable=True)
    phone_number = Column(String, nullable=True, index=True)
    address = Column(String, nullable=True, index=True)
    country = Column(String, nullable=True, index=True)
    verified_email = Column(Boolean, nullable=True, default=False, index=True)
    subscription = Column(String, nullable=True,  index=True)
    profile_pic = Column(String, nullable=True, index=True)
    token = Column(String, unique=True, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), index=True)

    # Relationships
    # upload_tasks = relationship("UploadTasks", back_populates="user")
    # pick_tasks = relationship("PickTasks", back_populates="user")
    # notifications = relationship("Notifications", back_populates="user")
    # submit_tasks = relationship("SubmitTasks", back_populates="user")

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

# class UploadTasks(Base):
#     __tablename__ = "upload_tasks"

#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, index=True)
#     user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
#     platform = Column(String, nullable=False, index=True) 
#     category = Column(String, nullable=False, index=True)  
#     type = Column(String, nullable=False, index=True)
#     content = Column(String, nullable=False, index=True)
#     description = Column(String, nullable=False, index=True)  
#     engagement = Column(Integer, nullable=False, index=True)
#     amount = Column(Integer, nullable=False, index=True )
#     status = Column(String, nullable=False, index=True)
#     created_at = Column(DateTime(timezone=True), default=func.now(), index=True)

#     # Relationships
#     user = relationship("Users", back_populates="upload_tasks")
#     pick_tasks = relationship("PickTasks", back_populates="upload_task")
#     submit_tasks = relationship("SubmitTasks", back_populates="upload_task")


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
