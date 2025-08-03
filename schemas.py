from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from uuid import UUID
from datetime import datetime
from typing import Literal, Dict



class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str
    status: Literal["success"]

class TokenRefreshRequest(BaseModel):
    refresh_token: str

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

class ResendCompanyCode(BaseModel):
    email: EmailStr 

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


class EmailSchema(BaseModel):
    email: EmailStr
    token: str


class AllCompanyResponse(companyBase):
    class Config:
        from_attributes = True
        fields = {
            'password': {'exclude': True}
        }

class LoginScheme(BaseModel):
    email: str
    password: str

class UpdateCompany(BaseModel):
    company_name: Optional[str]
    company_industry: Optional[str]
    phone_number: Optional[str]
    address: Optional[str]
    country: Optional[str]

    class Config:
        from_attributes = True

class UpdateCompanyResponse(BaseModel):
    status: str
    message: str
    company: UpdateCompany

class CoreDashboardReport(BaseModel):
    view_dashboard: bool = False
    export_data: bool = False
    generate_export_reports: bool = False
    view_sales_analytics: bool = False
    view_reports: bool = False

class LeadClientManagement(BaseModel):
    view_leads: bool = False
    view_clients: bool = False
    assign_lead: bool = False
    add_edit_clients: bool = False
    add_edit_leads: bool = False
    assign_client: bool = False

class OrderTaskManagement(BaseModel):
    view_orders: bool = False
    manage_orders: bool = False
    edit_tasks: bool = False
    create_edit_orders: bool = False
    assign_tasks: bool = False

class UserRoleManagement(BaseModel):
    view_users: bool = False
    manage_users: bool = False
    add_edit_users: bool = False
    assign_roles: bool = False

class BillingSubscription(BaseModel):
    view_billing: bool = False
    manage_billing: bool = False
    access_invoice: bool = False
    update_payment_method: bool = False


class IntegrationsApi(BaseModel):
    access_integration: bool = False
    manage_webhook: bool = False
    manage_api_keys: bool = False

class CommissionManagement(BaseModel):
    view_commission: bool = False
    approve_commission: bool = False

class NotificationManagement(BaseModel):
    manage_email_notification: bool = False
    manage_sms_notification: bool = False

class Permissions(BaseModel):
    core_dashboard_report: CoreDashboardReport
    lead_client_management: LeadClientManagement
    order_task_management: OrderTaskManagement
    user_role_management: UserRoleManagement
    billing_subscription: BillingSubscription
    integrations_api: IntegrationsApi
    commission_management: CommissionManagement
    notification_management: NotificationManagement

class StaffCreate(BaseModel):
    company_id: UUID
    full_name: str
    email: str
    password: str
    phone_number: str
    job_title: str
    department: str
    role: str
    permissions: Permissions

# class StaffResponse(BaseModel):
#     company_id: UUID
#     full_name: str
#     email: EmailStr
#     password: Optional[str]=None
#     phone_number: str
#     job_title: str
#     department: str
#     role: str
#     permissions: Permissions

    class Config:
        orm_mode = True


class StaffAccept(BaseModel):
    company_id: UUID
    email: str

class StaffPermissionUpdate(BaseModel):
    company_id: UUID
    staff_id: UUID
    permissions: Dict[str, bool]

# class StaffPermissionResponse(BaseModel):


class StaffLoginRequest(BaseModel):
    email: EmailStr

class StaffLoginResponse(BaseModel):
    id: UUID
class StaffVerifyResponse(BaseModel):
    id: UUID
    full_name: str
    email: EmailStr
    phone_number: str
    job_title: str
    department: str
    profile_pic: Optional[str]
    role: str
    permissions: Dict
    accept_invitation: bool
    created_at: datetime
    company_id: UUID

class StaffDelete(BaseModel):
    company_id: UUID
    staff_id: UUID
    permissions: Dict[str, bool]

