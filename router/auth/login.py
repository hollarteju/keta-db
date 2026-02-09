from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import User, Wallet, LedgerEntry, TransactionStatus, Transaction
from sqlalchemy import select, func, or_, desc
from schemas import Token, LoginScheme, AuthenticatedUserResponse, UserUpdate, UserProfileResponse, LoginPassword
from database import get_db, create_access_token, create_refresh_token
from utils.dependencies.auth import get_current_user
from utils.email_config import send_email
import random
from datetime import datetime, timedelta



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

    # Calculate total currency saved for each wallet
    wallet_balances = []
    total_usd_equivalent = 0  # You'll need exchange rates for this

    for wallet in wallets:
        # Get wallet balance from ledger entries
        balance_result = await db.execute(
            select(func.coalesce(func.sum(LedgerEntry.amount), 0))
            .where(LedgerEntry.wallet_id == wallet.id)
        )
        balance = balance_result.scalar_one()

        wallet_balances.append({
            "wallet_id": wallet.id,
            "currency": wallet.currency,
            "wallet_type": wallet.wallet_type.value,
            "balance": balance,
            "status": wallet.status.value,
        })

        # TODO: Convert to USD equivalent using exchange rates
        # For now, just sum if it's already USD
        if wallet.currency == "USD":
            total_usd_equivalent += balance

    # 📜 Get recent transaction history (max 10)
    # Get transactions where user is either sender or receiver
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

    # Format transaction history
    transaction_history = []
    for tx in transactions:
        # Determine if user is sender or receiver
        is_sender = tx.from_user_id == user_id
        
        # Get the other user's details
        other_user_id = tx.to_user_id if is_sender else tx.from_user_id
        other_user_result = await db.execute(
            select(User).where(User.id == other_user_id)
        )
        other_user = other_user_result.scalar_one_or_none()

        transaction_history.append({
            "id": tx.id,
            "header": tx.header.value,
            "description": tx.description,
            "type": tx.type.value,
            "status": tx.status.value,
            "from_currency": tx.from_currency,
            "to_currency": tx.to_currency,
            "from_amount": tx.from_amount,
            "to_amount": tx.to_amount,
            "rate": tx.rate,
            "reference": tx.reference,
            "created_at": tx.created_at,
            "is_sender": is_sender,
            "direction": "sent" if is_sender else "received",
            "other_user": {
                "id": other_user.id if other_user else None,
                "full_name": other_user.full_name if other_user else "Unknown",
                "profile_pic": other_user.profile_pic if other_user else None,
            } if other_user else None,
        })

    # 👥 Get quick transaction contacts (5 recent unique users)
    # Get unique users from recent transactions (excluding self)
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
            User.id != user_id,  # Exclude self
            Transaction.status == TransactionStatus.COMPLETED,  # Only completed transactions
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

    # 📊 Additional statistics
    # Total transactions count
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

    # Completed transactions count
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

    # Pending transactions count
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

    # 🎯 Build enhanced response
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

        # Wallet information
        "wallets": wallet_balances,
        "total_currency_saved": {
            "total_usd_equivalent": total_usd_equivalent,
            "breakdown": wallet_balances,
        },

        # Transaction history (max 10)
        "recent_transactions": transaction_history,

        # Quick transaction contacts (5 recent unique users)
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
