from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from uuid import UUID
from datetime import datetime


class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: str | None = None

class companyBase(BaseModel):
    id: UUID
    email: EmailStr  
    password: str
    company_name: Optional[str]= None
    company_industry: Optional[str]= None
    phone_number: Optional[str]= None
    address: Optional[str]= None
    country: Optional[str]= None
    verified_email: bool = False
    subscription: Optional[str]= None
    profile_pic: Optional[str] = None
    token: Optional[str] = None
    token_expire_at: Optional[str] = None

class CreateCompany(BaseModel):
    email: EmailStr  
    password: str

class CompanyResponse(BaseModel):
    id: UUID
    email: EmailStr
    created_at: Optional[datetime]

    model_config = {
        "from_attributes": True
    }

class RegisterCompanyResponse(BaseModel):
    status: str
    message: str
    company: CompanyResponse
    # class Config:
    #     from_attributes = True
    #     fields = {
    #         'password': {'exclude': True}
    #     }

class EmailSchema(BaseModel):
    email: EmailStr
    token: str


class AllCompanyResponse(companyBase):
    class Config:
        from_attributes = True
        fields = {
            'password': {'exclude': True}
        }

# class LoginScheme(BaseModel):
#     username_or_email: str
#     password: str

# class TaskCreateRequest(BaseModel):
#     platform: str
#     category: str
#     type: str
#     content: str
#     description: str
#     engagement: int
#     amount:int
#     status: str

# class GetTask(BaseModel):
#     platform: str 
#     category: str
#     type: str     

#     class Config:
#         from_attributes = True 

# class PickTaskRespond(BaseModel):
#     id: UUID 
#     user_id: UUID
#     task_id: UUID  
#     platform: str
#     category: str
#     uploader_name: str
#     type: str
#     status: str  
#     created_at: Optional[datetime]


#     class Config:
#         from_attributes = True 

# class SubmitTaskRequest(BaseModel):
#     task_id: UUID
#     image: str 
#     source: Optional[str] = None 

# class SubmitTaskResponse(BaseModel):
#     status: str

# class profilePicture(BaseModel):
#     image_url: str 

# class profilePictureResponse(BaseModel):
#     image_url: str