from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import User, Wallet, LedgerEntry, TransactionStatus, Transaction, CurrencySymbol, CurrencyType, TransactionDirection
from sqlalchemy import select, func, or_, desc
from schemas import Token, LoginScheme, AuthenticatedUserResponse, UserUpdate, UserProfileResponse, LoginPassword
from database import get_db, create_access_token, create_refresh_token
from utils.dependencies.auth import get_current_user
from utils.email_config import send_email
import random
from datetime import datetime, timedelta
from collections import defaultdict


def format_tx_amount(tx, is_sender: bool):
    if is_sender:
        return f"-{tx.from_amount} {tx.from_currency}"
    return f"+{tx.to_amount} {tx.to_currency}"

def format_date_label(dt: datetime):
    return dt.strftime("%b %d")  # Oct 25

CURRENCY_FLAG = {
    "NGN": "🇳🇬",
    "USD": "🇺🇸",
    "EUR": "🇪🇺",
    "POUND": "🇬🇧",
    "GBP": "🇬🇧",
}   


CURRENCY_NAME = {
    "NGN": "Nigerian Naira",
    "USD": "US Dollar",
    "EUR": "🇪🇺",
    "POUND": "🇬🇧",
    "GBP": "🇬🇧",
}   




router = APIRouter(
    prefix="/api/v1",
    tags=["users"]
)


@router.post("/user/login", response_model=Token)
async def login_for_access_token(requests: LoginScheme, db: AsyncSession = Depends(get_db)):
   
    payload = select(User).filter(
        User.email == requests.email
    )

    result = await db.execute(payload)
    user = result.scalar_one_or_none()
    
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.verify_password(requests.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.verified_email:
        token = f"{random.randrange(10**5):05}"
        token_expires_at = datetime.utcnow() + timedelta(minutes=10)

        user.token = token
        user.token_expires_at = token_expires_at

        await db.commit()
        await  send_email(user.email, str(token), "keta-sign-up")


        return Token(
        access_token=access_token, 
        refresh_token=refresh_token,
        token_type="bearer",
        status="success"
        )
   
    return Token(
        access_token=access_token, 
        refresh_token=refresh_token,
        token_type="bearer",
        status="success"
        )



@router.post("/me", response_model=UserProfileResponse)
async def get_me(
    credentials: LoginPassword,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not user.verify_password(credentials.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    return await get_enhanced_user_profile(db, user.id)



@router.get("/me", response_model=UserProfileResponse)
async def get_me(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    enhanced_user_data = await get_enhanced_user_profile(db, user.id)
   
    return enhanced_user_data


async def get_enhanced_user_profile(db: AsyncSession, user_id: str):
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 💰 Get all user wallets with balances
    wallet_result = await db.execute(
        select(Wallet).where(Wallet.user_id == user_id)
    )
    wallets = wallet_result.scalars().all()

    # Calculate total currency saved and separate default wallet
    wallet_balances = []
    total_usd_equivalent = 0
    default_wallet = None

    for wallet in wallets:
        # Get wallet balance from ledger entries
        balance_result = await db.execute(
            select(func.coalesce(func.sum(LedgerEntry.amount), 0))
            .where(LedgerEntry.wallet_id == wallet.id)
        )
        balance = balance_result.scalar_one()
        symbol = CurrencySymbol.CURRENCY_SYMBOL.get(CurrencyType(wallet.currency), wallet.currency)

        # Example wallet data
        wallet_data = {
            "wallet_id": wallet.id,
            "currency": wallet.currency,
            "wallet_type": wallet.wallet_type,
            "symbol": symbol,
            "balance": balance,
            "status": wallet.status,
            "flag": CURRENCY_FLAG.get(wallet.currency),
            "name" : CURRENCY_NAME.get(wallet.currency) 
        }

        wallet_balances.append(wallet_data)

        # Assign default wallet as USD if exists
        if wallet.currency == "USD" and default_wallet is None:
            default_wallet = wallet_data
            total_usd_equivalent += balance
        elif wallet.currency != "USD":
            # You can optionally convert to USD using exchange rates
            pass

    # If no USD wallet exists, pick the first as default
    if not default_wallet and wallet_balances:
        default_wallet = wallet_balances[0]

    # 📜 Get recent transactions (max 10)
    transaction_result = await db.execute(
        select(Transaction)
        .where(
            or_(
                Transaction.from_user_id == user_id,
                Transaction.to_user_id == user_id
            )
        )
        .order_by(desc(Transaction.created_at))
        .limit(10)
    )
    transactions = transaction_result.scalars().all()

    grouped = defaultdict(list)
    for tx in transactions:
        date_key = format_date_label(tx.created_at)
        grouped[date_key].append({
            "header": tx.header,
            "description": tx.description,
            "amount": tx.formatted_amount(),
            "status": tx.status,
            "icon": (
        "arrow-up" if tx.type in TransactionDirection.CREDIT_TYPES else
        "arrow-down" if tx.type in TransactionDirection.DEBIT_TYPES else
        "arrow-right"
        ),
        "color": (
            "#22C55E" if tx.type in TransactionDirection.CREDIT_TYPES else
            "#EF4444" if tx.type in TransactionDirection.DEBIT_TYPES else
            "#6B7280"
        ),
        })

    recent_transactions = [
        {"created_at": date, "data": items}
        for date, items in grouped.items()
    ]

    # 👥 Quick transaction contacts
    quick_contacts_result = await db.execute(
        select(User)
        .join(
            Transaction,
            or_(
                Transaction.from_user_id == User.id,
                Transaction.to_user_id == User.id
            )
        )
        .where(
            or_(
                Transaction.from_user_id == user_id,
                Transaction.to_user_id == user_id
            ),
            User.id != user_id,
            Transaction.status == TransactionStatus.COMPLETED
        )
        .group_by(User.id)
        .order_by(desc(func.max(Transaction.created_at)))
        .limit(5)
    )
    quick_contacts_users = quick_contacts_result.scalars().all()

    quick_transaction_contacts = [
        {
            "id": contact.id,
            "full_name": contact.full_name,
            "profile_pic": contact.profile_pic,
            "email": contact.email,
        }
        for contact in quick_contacts_users
    ]

    # 📊 Statistics
    total_tx_result = await db.execute(
        select(func.count(Transaction.id))
        .where(
            or_(
                Transaction.from_user_id == user_id,
                Transaction.to_user_id == user_id
            )
        )
    )
    total_transactions = total_tx_result.scalar_one()

    completed_tx_result = await db.execute(
        select(func.count(Transaction.id))
        .where(
            or_(
                Transaction.from_user_id == user_id,
                Transaction.to_user_id == user_id
            ),
            Transaction.status == TransactionStatus.COMPLETED
        )
    )
    completed_transactions = completed_tx_result.scalar_one()

    pending_tx_result = await db.execute(
        select(func.count(Transaction.id))
        .where(
            or_(
                Transaction.from_user_id == user_id,
                Transaction.to_user_id == user_id
            ),
            Transaction.status == TransactionStatus.PENDING
        )
    )
    pending_transactions = pending_tx_result.scalar_one()

    return {
        # Basic user info
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "phone_number": user.phone_number,
        "address": user.address,
        "country": user.country,
        "verified_email": user.verified_email,
        "subscription": user.subscription,
        "profile_pic": user.profile_pic,
        "active": user.active,
        "created_at": user.created_at,

        # Wallets
        "wallets": wallet_balances,
        "default_wallet": default_wallet,
        "total_currency_saved": {
            "total_usd_equivalent": total_usd_equivalent,
            "breakdown": wallet_balances,
        },

        # Transactions
        "recent_transactions": recent_transactions,
        "quick_transaction_contacts": quick_transaction_contacts,

        # Statistics
        "statistics": {
            "total_transactions": total_transactions,
            "completed_transactions": completed_transactions,
            "pending_transactions": pending_transactions,
            "total_wallets": len(wallets),
        },
    }


@router.patch("/update/me", response_model=AuthenticatedUserResponse)
async def update_me(
    payload: UserUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    # Update fields if they are provided
    if payload.full_name is not None:
        user.full_name = payload.full_name

    if payload.profile_pic is not None:
        user.profile_pic = payload.profile_pic

    # Save changes
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user
