from pydantic import BaseModel, EmailStr, field_validator, Field, StringConstraints, condecimal
from typing import Optional, List, Annotated
from uuid import UUID
from datetime import datetime, date, time as dtime
from typing import Literal, Dict, Any
from enum import Enum
from decimal import Decimal


SixDigitPassword = Annotated[
    str,
    StringConstraints(pattern=r"^\d{6}$")
]
class WalletTypeEnum(str, Enum):
    FIAT = "fiat"
    CRYPTO = "crypto"


class WalletStatusEnum(str, Enum):
    ACTIVE = "active"
    FROZEN = "frozen"


class TransactionTypeEnum(str, Enum):
    BUY = "buy"
    SELL = "sell"
    EXCHANGE = "exchange"
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    WALLET_FUND = "WALLET_FUND"


class TransactionStatusEnum(str, Enum):
    PENDING = "Pending"
    PROCESSING = "Processing"
    COMPLETED = "Completed"
    FAILED = "Failed"
    FUND_RELEASED = "Fund released"
    UNDER_REVIEW = "Under review"
    CANCELLED = "Cancelled"


class TransactionHeaderEnum(str, Enum):
    CRYPTO_PURCHASE = "Crypto Purchase Completed"
    CRYPTO_SALE = "Crypto Sale Completed"


class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str
    status: Literal["success", "failed"]

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

class CreateUser(BaseModel):
    full_name: str
    email: EmailStr  
    password: SixDigitPassword

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    profile_pic: Optional[str] = None

    class Config:
        orm_mode = True

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    address: Optional[str] = None
    country: Optional[str] = None
    verified_email: bool
    subscription: Optional[str] = None
    profile_pic: Optional[str] = None
    active: bool
    created_at: Optional[datetime] = None   # <-- make optional

    class Config:
        orm_mode = True
        
class ResendCompanyCode(BaseModel):
    email: EmailStr 

class ResendStaffCode(BaseModel):
    email: EmailStr 

class UserResponse(BaseModel):
    id: UUID
    full_name: str
    email: EmailStr
    created_at: Optional[datetime]

    model_config = {
        "from_attributes": True
    }

class RegisterUserResponse(BaseModel):
    status: str
    message: str
    company: UserResponse


class EmailSchema(BaseModel):
    email: EmailStr
    token: str

class AuthenticatedUserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    phone_number: Optional[str]
    address: Optional[str]
    country: Optional[str]
    verified_email: bool
    subscription: Optional[str]
    profile_pic: Optional[str]
    active: Optional[bool]
    created_at: datetime

    class Config:
        from_attributes = True

class AllCompanyResponse(companyBase):
    class Config:
        from_attributes = True
        fields = {
            'password': {'exclude': True}
        }

class LoginScheme(BaseModel):
    email: str
    password: SixDigitPassword

class LoginPassword(BaseModel):
    password: SixDigitPassword

class UpdateUser(BaseModel):
    company_name: Optional[str]
    phone_number: Optional[str]
    address: Optional[str]
    country: Optional[str]

    class Config:
        from_attributes = True

class UpdateUserResponse(BaseModel):
    status: str
    message: str
    company: UpdateUser

class WalletBalance(BaseModel):
    """Individual wallet balance information"""
    wallet_id: str = Field(..., description="Unique wallet identifier")
    currency: str = Field(..., description="Currency code (USD, BTC, ETH, etc.)")
    wallet_type: str = Field(..., description="Type of wallet (fiat or crypto)")
    symbol: str
    flag:str
    name: str
    balance: int = Field(..., description="Current balance in smallest unit (cents, satoshis, wei)")
    status: str = Field(..., description="Wallet status (active or frozen)")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "wallet_id": "wallet-uuid-123",
                "currency": "USD",
                "wallet_type": "fiat",
                "balance": 150000,
                "status": "active"
            }
        }


class TotalCurrencySaved(BaseModel):
    """Total currency saved across all wallets"""
    total_usd_equivalent: int = Field(
        ..., 
        description="Total value in USD cents (requires exchange rate conversion for crypto)"
    )
    breakdown: List[WalletBalance] = Field(
        ..., 
        description="Detailed breakdown of all wallet balances"
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "total_usd_equivalent": 150000,
                "breakdown": [
                    {
                        "wallet_id": "wallet-uuid-1",
                        "currency": "USD",
                        "wallet_type": "fiat",
                        "balance": 150000,
                        "status": "active"
                    }
                ]
            }
        }


class OtherUserInTransaction(BaseModel):
    """Other user details in a transaction"""
    id: Optional[str] = Field(None, description="User's unique identifier")
    full_name: Optional[str] = Field(None, description="User's full name")
    profile_pic: Optional[str] = Field(None, description="URL to user's profile picture")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "user-uuid-456",
                "full_name": "Jane Smith",
                "profile_pic": "https://example.com/jane.jpg"
            }
        }

class TransactionUIMeta(BaseModel):
    icon: str = Field(
        ...,
        description="Icon representing transaction direction (arrow-up / arrow-down)"
    )
    color: str = Field(
        ...,
        description="Hex color representing transaction type (green for incoming, red for outgoing)"
    )
class TransactionHistoryItem(BaseModel):
    """Individual transaction history item"""
    id: str = Field(..., description="Transaction unique identifier")
    header: str = Field(..., description="Transaction header/title")
    description: str = Field(..., description="Detailed transaction description")
    type: str = Field(..., description="Transaction type (buy, sell, exchange, deposit, withdrawal)")
    status: str = Field(..., description="Current transaction status")
    from_currency: Optional[str] = Field(None, description="Source currency")
    to_currency: Optional[str] = Field(None, description="Destination currency")
    from_amount: int = Field(..., description="Amount sent/sold in smallest unit")
    to_amount: Optional[int] = Field(None, description="Amount received/bought in smallest unit")
    rate: Optional[int] = Field(None, description="Exchange rate used (multiplied for precision)")
    reference: Optional[str] = Field(None, description="Transaction reference number")
    created_at: datetime = Field(..., description="Transaction timestamp")
    is_sender: bool = Field(..., description="True if current user is the sender")
    direction: str = Field(..., description="Transaction direction: 'sent' or 'received'")
    ui: TransactionUIMeta
    other_user: Optional[OtherUserInTransaction] = Field(
        None, 
        description="Details of the other party in the transaction"
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "tx-uuid-789",
                "header": "Crypto Purchase Completed",
                "description": "You bought 0.5 BTC for $25,000 USD",
                "type": "buy",
                "status": "Completed",
                "from_currency": "USD",
                "to_currency": "BTC",
                "from_amount": 2500000,
                "to_amount": 50000000,
                "rate": 5000000,
                "reference": "REF-20240115-001",
                "created_at": "2024-01-15T14:30:00.000Z",
                "is_sender": True,
                "direction": "sent",
                "other_user": {
                    "id": "user-uuid-456",
                    "full_name": "Jane Smith",
                    "profile_pic": "https://example.com/jane.jpg"
                }
            }
        }

class TransactionUIItem(BaseModel):
    """Single transaction item formatted for wallet UI"""
    header: str
    description: Optional[str]
    amount: str
    status: str
    icon: str
    color: str


class TransactionGroup(BaseModel):
    """Transactions grouped by date for wallet activity screen"""
    created_at: str
    data: List[TransactionUIItem]

class QuickTransactionUser(BaseModel):
    """Quick transaction contact information"""
    id: str = Field(..., description="User's unique identifier")
    full_name: Optional[str] = Field(None, description="User's full name")
    profile_pic: Optional[str] = Field(None, description="URL to user's profile picture")
    email: str = Field(..., description="User's email address")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "user-uuid-456",
                "full_name": "Jane Smith",
                "profile_pic": "https://example.com/jane.jpg",
                "email": "jane.smith@example.com"
            }
        }


class UserStatistics(BaseModel):
    """User transaction and wallet statistics"""
    total_transactions: int = Field(
        ..., 
        description="Total number of transactions (sent + received)"
    )
    completed_transactions: int = Field(
        ..., 
        description="Number of completed transactions"
    )
    pending_transactions: int = Field(
        ..., 
        description="Number of pending transactions"
    )
    total_wallets: int = Field(
        ..., 
        description="Total number of wallets owned by user"
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "total_transactions": 45,
                "completed_transactions": 38,
                "pending_transactions": 5,
                "total_wallets": 3
            }
        }



# Main response schema
class UserProfileResponse(BaseModel):
    """
    Enhanced user profile response with transaction history, 
    quick contacts, and wallet information
    """
    
    # Basic user information
    id: str = Field(..., description="User's unique identifier (UUID)")
    email: str = Field(..., description="User's email address")
    full_name: Optional[str] = Field(None, description="User's full name")
    phone_number: Optional[str] = Field(None, description="User's phone number")
    address: Optional[str] = Field(None, description="User's physical address")
    country: Optional[str] = Field(None, description="User's country")
    verified_email: bool = Field(..., description="Email verification status")
    subscription: Optional[str] = Field(None, description="Subscription tier (e.g., premium, basic)")
    profile_pic: Optional[str] = Field(None, description="URL to user's profile picture")
    active: Optional[bool] = Field(None, description="Account active status")
    created_at: datetime = Field(..., description="Account creation timestamp")

    # Wallet information
    wallets: List[WalletBalance] = Field(
        default_factory=list,
        description="List of all user wallets with current balances"
    )
    default_wallet: Optional[WalletBalance] = None
    total_currency_saved: TotalCurrencySaved = Field(
        ...,
        description="Total currency saved across all wallets with breakdown"
    )

    # Transaction history (max 10 recent)
    recent_transactions: List[TransactionGroup] = Field(
        default_factory=list,
        description="List of recent transactions (maximum 10, most recent first)"
    )

    # Quick transaction contacts (5 recent unique users)
    quick_transaction_contacts: List[QuickTransactionUser] = Field(
        default_factory=list,
        description="List of frequently transacted users (maximum 5, most recent first)"
    )

    # Statistics
    statistics: UserStatistics = Field(
        ...,
        description="User transaction and wallet statistics"
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "john.doe@example.com",
                "full_name": "John Doe",
                "phone_number": "+1234567890",
                "address": "123 Main St, New York, NY 10001",
                "country": "United States",
                "verified_email": True,
                "subscription": "premium",
                "profile_pic": "https://example.com/profile.jpg",
                "active": True,
                "created_at": "2024-01-15T10:30:00.000Z",
                "wallets": [
                    {
                        "wallet_id": "wallet-uuid-1",
                        "currency": "USD",
                        "wallet_type": "fiat",
                        "balance": 150000,
                        "status": "active"
                    },
                    {
                        "wallet_id": "wallet-uuid-2",
                        "currency": "BTC",
                        "wallet_type": "crypto",
                        "balance": 50000000,
                        "status": "active"
                    }
                ],
                
                "total_currency_saved": {
                    "total_usd_equivalent": 150000,
                    "breakdown": [
                        {
                            "wallet_id": "wallet-uuid-1",
                            "currency": "USD",
                            "wallet_type": "fiat",
                            "balance": 150000,
                            "status": "active"
                        },
                        {
                            "wallet_id": "wallet-uuid-2",
                            "currency": "BTC",
                            "wallet_type": "crypto",
                            "balance": 50000000,
                            "status": "active"
                        }
                    ]
                },
                "recent_transactions": [
                    {
                        "id": "tx-uuid-1",
                        "header": "Crypto Purchase Completed",
                        "description": "You bought 0.5 BTC for $25,000 USD",
                        "type": "buy",
                        "status": "Completed",
                        "from_currency": "USD",
                        "to_currency": "BTC",
                        "from_amount": 2500000,
                        "to_amount": 50000000,
                        "rate": 5000000,
                        "reference": "REF-20240115-001",
                        "created_at": "2024-01-15T14:30:00.000Z",
                        "is_sender": True,
                        "direction": "sent",
                        "ui": {
                            "icon": "arrow-down",
                            "color": "#EF4444"
                        },
                        "other_user": {
                            "id": "user-uuid-2",
                            "full_name": "Jane Smith",
                            "profile_pic": "https://example.com/jane.jpg"
                        }
                    }
                ],
                "quick_transaction_contacts": [
                    {
                        "id": "user-uuid-2",
                        "full_name": "Jane Smith",
                        "profile_pic": "https://example.com/jane.jpg",
                        "email": "jane.smith@example.com"
                    },
                    {
                        "id": "user-uuid-3",
                        "full_name": "Bob Johnson",
                        "profile_pic": "https://example.com/bob.jpg",
                        "email": "bob.johnson@example.com"
                    }
                ],
                "statistics": {
                    "total_transactions": 45,
                    "completed_transactions": 38,
                    "pending_transactions": 5,
                    "total_wallets": 2
                }
            }
        }


class WalletResponse(BaseModel):
    id: str
    user_id: str
    currency: str
    wallet_type: str
    status: str
    balance: Decimal = 0
    total_credit: Decimal = 0
    total_debit: Decimal = 0
    transaction_count: int = 0
    created_at: datetime

    class Config:
        orm_mode = True


class FundWalletRequest(BaseModel):
    user_id: str
    amount: condecimal(gt=0, decimal_places=2) 


class WalletResponse(BaseModel):
    id: str
    user_id: str
    currency: str
    wallet_type: str
    status: str
    balance: Decimal
    total_credit: Decimal
    total_debit: Decimal
    transaction_count: int
    created_at: datetime

class DevFundWalletRequest(BaseModel):
    user_id: str
    amount: int
    currency: str = "NGN"

class VerifyAccountRequest(BaseModel):
    account_number: str
    bank_code: str

class VerifyAccountResponse(BaseModel):
    account_number: str
    account_name: str
    bank_code: str
