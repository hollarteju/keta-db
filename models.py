import uuid
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Date, Time, Text, Enum, JSON
from sqlalchemy.orm import relationship
from database import Base
from sqlalchemy.sql import func
from passlib.context import CryptContext
from datetime import datetime, date, time, timedelta
from enum import Enum as PyEnum



pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
def str_to_uuid(value: str) -> uuid.UUID:
    """Convert string to UUID if value is not None/empty."""
    return uuid.UUID(value) if value else None

class AttendanceStatus(PyEnum):
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"
    EARLY_DEPARTURE = "early_departure"
    ON_LEAVE = "on_leave"

class LeaveType(PyEnum):
    SICK = "sick"
    VACATION = "vacation"
    PERSONAL = "personal"
    EMERGENCY = "emergency"
    MATERNITY = "maternity"
    PATERNITY = "paternity"


class TaskPriority(PyEnum):
    IMPORTANT = "important"
    NORMAL = "normal"
    LOW = "low"

class TaskStatus(PyEnum):
    pending = "pending"
    completed = "completed"
    overdue = "overdue"



class Companies(Base):
    __tablename__ = "companies"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), unique=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    company_name = Column(String(100), index=True, nullable=True)
    company_industry = Column(String(100), index=True, nullable=True)
    phone_number = Column(String(20), nullable=True, index=True)
    address = Column(String(255), nullable=True, index=True)
    country = Column(String(100), nullable=True, index=True)
    verified_email = Column(Boolean, nullable=True, default=False, index=True)
    subscription = Column(String(50), nullable=True, index=True)
    profile_pic = Column(String(225), nullable=True, index=True)
    active = Column(Boolean, nullable=True, default=False)  # Changed to Boolean
    token = Column(String(225), unique=True, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), index=True)
    
    # Work schedule settings
    # default_work_start_time = Column(Time, default=time(8, 0))  # 8:00 AM
    # default_work_end_time = Column(Time, default=time(17, 0))   # 5:00 PM
    # grace_period_minutes = Column(Integer, default=15)  # 15 minutes late tolerance
    
    # Relationships
    company_staffs = relationship("CompanyStaffs", back_populates="companies", cascade="all, delete-orphan")
    attendance_records = relationship("AttendanceRecord", back_populates="company", cascade="all, delete-orphan")
    # leave_requests = relationship("LeaveRequest", back_populates="company", cascade="all, delete-orphan")
    
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
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), unique=True, index=True)
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=False)
    full_name = Column(String(100), nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False, index=True)
    phone_number = Column(String(20), nullable=False, index=True)
    job_title = Column(String(100), nullable=False, index=True)
    department = Column(String(100), nullable=False, index=True)
    profile_pic = Column(String(225), nullable=True, index=True)
    role = Column(String(100), nullable=False, index=True)
    permissions = Column(JSON, nullable=False, index=True, default={})
    accept_invitation = Column(Boolean, default=False)  # Fixed syntax
    token = Column(String(225), nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), index=True)
    
    # Staff-specific work schedule (overrides company defaults if set)
    # work_start_time = Column(Time, nullable=True)  # Custom start time
    # work_end_time = Column(Time, nullable=True)    # Custom end time

    is_active = Column(Boolean, default=True, index=True)
    
    # Relationships
    companies = relationship("Companies", back_populates="company_staffs")
    attendance_records = relationship("AttendanceRecord", back_populates="staff", cascade="all, delete-orphan")
    # leave_requests = relationship("LeaveRequest", back_populates="staff", cascade="all, delete-orphan")
    
    def validate_token(self, token: str):
        if self.token != token:
            raise ValueError("Invalid verification token")
        elif self.token_expires_at is None or self.token_expires_at < datetime.utcnow():
            raise ValueError("Verification token has expired")
    
    # def get_work_schedule(self):
    #     """Get effective work schedule (staff-specific or company default)"""
    #     company = self.companies
    #     return {
    #         'start_time': self.work_start_time or company.default_work_start_time,
    #         'end_time': self.work_end_time or company.default_work_end_time,
    #         'grace_period': company.grace_period_minutes
    #     }
    def company_uuid(self) -> uuid.UUID:
        return str_to_uuid(self.company_id)


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), unique=True, index=True)
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
    staff_id = Column(String(36), ForeignKey("company_staffs.id"), nullable=False, index=True)
    
    # Date and time tracking
    attendance_date = Column(Date, nullable=False, index=True)
    check_in_time = Column(DateTime(timezone=True), nullable=True)
    check_out_time = Column(DateTime(timezone=True), nullable=True)
    
    # Status and calculations
    # status = Column(Enum(AttendanceStatus), nullable=False, default=AttendanceStatus.ABSENT, index=True)
    # is_late = Column(Boolean, default=False, index=True)
    # late_minutes = Column(Integer, default=0)
    # early_departure = Column(Boolean, default=False, index=True)
    # early_departure_minutes = Column(Integer, default=0)
    
    # Work hours calculation
    # total_work_hours = Column(Integer, nullable=True)  # in minutes
    # break_time_minutes = Column(Integer, default=0)
    # overtime_minutes = Column(Integer, default=0)
    
    # Additional information
    # check_in_location = Column(JSON, nullable=True)  # GPS coordinates, IP address
    # check_out_location = Column(JSON, nullable=True)
    # notes = Column(Text, nullable=True)  # Staff or admin notes
    
    # System tracking
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # Relationships
    company = relationship("Companies", back_populates="attendance_records")
    staff = relationship("CompanyStaffs", back_populates="attendance_records")

    def company_uuid(self) -> uuid.UUID:
        """Return company_id as UUID object."""
        return str_to_uuid(self.company_id)
    
    def staff_uuid(self) -> uuid.UUID:
        """Return staff_id as UUID object."""
        return str_to_uuid(self.staff_id)
    


class Tasks(Base):
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), unique=True, index=True)

    # Optional: Link to a company or staff member
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=True, index=True)
    staff_id = Column(String(36), ForeignKey("company_staffs.id"), nullable=True, index=True)

    # Task details
    task_title = Column(String(150), nullable=False, index=True)
    task_type = Column(String(100), nullable=False, index=True)
    customer_name = Column(String(100), nullable=False, index=True)
    customer_phone = Column(String(20), nullable=False, index=True)
    description = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)
    date = Column(Date, nullable=False, index=True)
    time = Column(Time, nullable=True, index=True)
    priority = Column(Enum(TaskPriority), nullable=False, default=TaskPriority.NORMAL, index=True)
    attachment = Column(JSON, nullable=True)  # Can store multiple file URLs or metadata
    status = Column(Enum(TaskStatus), default=TaskStatus.pending, nullable=False)

    # System tracking
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    company = relationship("Companies", backref="tasks", lazy="joined")
    staff = relationship("CompanyStaffs", backref="tasks", lazy="joined")

    def __repr__(self):
        return f"<Task(title='{self.task_title}', type='{self.task_type}', priority='{self.priority.value}')>"


    
    # def calculate_work_hours(self):
    #     """Calculate total work hours and overtime"""
    #     if not self.check_in_time or not self.check_out_time:
    #         return
        
    #     # Calculate total time worked
    #     work_duration = self.check_out_time - self.check_in_time
    #     total_minutes = int(work_duration.total_seconds() / 60)
        
    #     # Subtract break time
    #     actual_work_minutes = total_minutes - self.break_time_minutes
    #     self.total_work_hours = max(0, actual_work_minutes)
        
    #     # Calculate overtime (assuming 8 hours = 480 minutes standard)
    #     standard_work_minutes = 480
    #     if actual_work_minutes > standard_work_minutes:
    #         self.overtime_minutes = actual_work_minutes - standard_work_minutes
    
    # def determine_status(self):
    #     """Determine attendance status based on check-in/out times"""
    #     if not self.check_in_time:
    #         self.status = AttendanceStatus.ABSENT
    #         return
        
    #     schedule = self.staff.get_work_schedule()
    #     scheduled_start = datetime.combine(self.attendance_date, schedule['start_time'])
    #     scheduled_end = datetime.combine(self.attendance_date, schedule['end_time'])
        
    #     # Check if late
    #     grace_period_end = scheduled_start + timedelta(minutes=schedule['grace_period'])
    #     if self.check_in_time > grace_period_end:
    #         self.is_late = True
    #         self.late_minutes = int((self.check_in_time - scheduled_start).total_seconds() / 60)
    #         self.status = AttendanceStatus.LATE
        
    #     # Check early departure
    #     if self.check_out_time and self.check_out_time < scheduled_end:
    #         self.early_departure = True
    #         self.early_departure_minutes = int((scheduled_end - self.check_out_time).total_seconds() / 60)
    #         if self.status != AttendanceStatus.LATE:
    #             self.status = AttendanceStatus.EARLY_DEPARTURE
        
    #     # If not late or early departure, mark as present
    #     if self.status == AttendanceStatus.ABSENT and not self.is_late and not self.early_departure:
    #         self.status = AttendanceStatus.PRESENT

# class LeaveRequest(Base):
#     __tablename__ = "leave_requests"
    
    # id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), unique=True, index=True)
#     company_id = Column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
#     staff_id = Column(String(36), ForeignKey("company_staffs.id"), nullable=False, index=True)
    
#     # Leave details
#     leave_type = Column(Enum(LeaveType), nullable=False, index=True)
#     start_date = Column(Date, nullable=False, index=True)
#     end_date = Column(Date, nullable=False, index=True)
#     total_days = Column(Integer, nullable=False)
#     reason = Column(Text, nullable=True)
    
#     # Approval workflow
#     status = Column(String(20), default="pending", index=True)  # pending, approved, rejected
#     approved_by = Column(String(36), ForeignKey("company_staffs.id"), nullable=True)
#     approved_at = Column(DateTime(timezone=True), nullable=True)
#     rejection_reason = Column(Text, nullable=True)
    
#     # Supporting documents
#     documents = Column(JSON, nullable=True)  # URLs to uploaded documents
    
#     # System tracking
#     created_at = Column(DateTime(timezone=True), default=func.now(), index=True)
#     updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
#     # Relationships
#     company = relationship("Companies", back_populates="leave_requests")
#     staff = relationship("CompanyStaffs", back_populates="leave_requests")
#     approver = relationship("CompanyStaffs", foreign_keys=[approved_by])

# class AttendanceSummary(Base):
#     """Monthly attendance summary for reporting and analytics"""
#     __tablename__ = "attendance_summaries"
    
    # id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), unique=True, index=True)
#     company_id = Column(String(36), ForeignKey("companies.id"), nullable=False, index=True)
#     staff_id = Column(String(36), ForeignKey("company_staffs.id"), nullable=False, index=True)
    
#     # Period
#     year = Column(Integer, nullable=False, index=True)
#     month = Column(Integer, nullable=False, index=True)
    
#     # Summary statistics
#     total_working_days = Column(Integer, default=0)
#     days_present = Column(Integer, default=0)
#     days_absent = Column(Integer, default=0)
#     days_late = Column(Integer, default=0)
#     days_on_leave = Column(Integer, default=0)
    
#     total_work_hours = Column(Integer, default=0)  # in minutes
#     total_overtime_hours = Column(Integer, default=0)  # in minutes
#     total_late_minutes = Column(Integer, default=0)
    
#     # System tracking
#     generated_at = Column(DateTime(timezone=True), default=func.now())
    
#     # Relationships
#     company = relationship("Companies")
#     staff = relationship("CompanyStaffs")