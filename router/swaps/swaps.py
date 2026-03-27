from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from decimal import Decimal

from database import get_db
from models import Swap, Wallet, SwapStatus, Transaction, TransactionType, TransactionStatus, SwapExecution, InsufficientFundsError, CurrencyType, User
from schemas import SwapCreate, SwapUpdate
from models import Wallet
from utils.rates import fetch_currency_rates
from uuid import uuid4
from datetime import datetime
from utils.dependencies.auth import get_current_user


router = APIRouter(prefix="/swaps", tags=["Swaps"])


@router.post("/")
async def create_swap(data: SwapCreate, db: AsyncSession = Depends(get_db)):

    wallet_result = await db.execute(
        select(Wallet).where(Wallet.id == data.wallet_id)
    )
    wallet = wallet_result.scalar_one_or_none()

    if not wallet:
        raise HTTPException(404, "Wallet not found")

    if wallet.currency != data.from_currency:
        raise HTTPException(400, "Wallet currency mismatch")

    # lock funds
    await Wallet.lock_balance(db, wallet.id, data.amount)

    swap = Swap(
        wallet_id=data.wallet_id,
        creator_id=wallet.user_id,
        from_currency=data.from_currency,
        to_currency=data.to_currency,
        amount=data.amount,
        min_amount=data.min_amount,
        remaining_amount=data.amount,
        rate=data.rate,
        expires_at=data.expires_at
    )

    db.add(swap)
    await db.commit()
    await db.refresh(swap)

    return swap


@router.get("/")
async def get_all_swaps(db: AsyncSession = Depends(get_db)):

    result = await db.execute(
        select(Swap).where(Swap.status == SwapStatus.OPEN)
    )

    swaps = result.scalars().all()

    return swaps


@router.get("/me")
async def get_user_swaps(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):

    result = await db.execute(
        select(Swap).where(Swap.creator_id == user.id)
    )

    swaps = result.scalars().all()

    return swaps


@router.patch("/{swap_id}")
async def update_swap(
    swap_id: str,
    data: SwapUpdate,
    db: AsyncSession = Depends(get_db)
):

    result = await db.execute(
        select(Swap).where(Swap.id == swap_id)
    )

    swap = result.scalar_one_or_none()

    if not swap:
        raise HTTPException(404, "Swap not found")

    if swap.status != SwapStatus.OPEN:
        raise HTTPException(400, "Cannot update completed swap")

    if data.rate:
        swap.rate = data.rate

    if data.expires_at:
        swap.expires_at = data.expires_at

    db.add(swap)
    await db.commit()
    await db.refresh(swap)

    return swap



@router.delete("/{swap_id}")
async def cancel_swap(swap_id: str, db: AsyncSession = Depends(get_db)):

    result = await db.execute(
        select(Swap).where(Swap.id == swap_id)
    )

    swap = result.scalar_one_or_none()

    if not swap:
        raise HTTPException(404, "Swap not found")

    if swap.status != SwapStatus.OPEN:
        raise HTTPException(400, "Swap cannot be cancelled")

    # unlock funds
    await Wallet.unlock_balance(db, swap.wallet_id, swap.remaining_amount)

    swap.status = SwapStatus.CANCELLED

    db.add(swap)
    await db.commit()

    return {"message": "Swap cancelled"}



@router.post("/buy/initiate/{swap_id}")
async def initiate_swap_purchase(
    swap_id: str,
    amount: Decimal = Query(..., description="Amount of swap currency to buy"),
    pay_currency: CurrencyType = Query(..., description="Currency buyer will pay with"),
    user_id: str = Query(..., description="Buyer user ID (from auth token)"),
    db: AsyncSession = Depends(get_db)
):
    # 1️⃣ Get the swap
    result = await db.execute(select(Swap).where(Swap.id == swap_id))
    swap: Swap = result.scalar_one_or_none()
    if not swap or swap.status in ["filled", "cancelled"]:
        raise HTTPException(status_code=400, detail="Swap not available")

    if not swap.validate_order_amount(amount):
        raise HTTPException(status_code=401, detail="Invalid trade amount")
    # 2️⃣ Get buyer wallet (in the currency they pay with)
    result = await db.execute(
        select(Wallet).where(Wallet.user_id == user_id, Wallet.currency == pay_currency.value)
    )
    buyer_wallet: Wallet = result.scalar_one_or_none()
    if not buyer_wallet:
        raise HTTPException(status_code=400, detail=f"Buyer wallet not found for {pay_currency.value}")

    # 3️⃣ Calculate total cost based on swap rate
    # Assuming swap.rate = units of pay_currency per 1 unit of swap.from_currency
    
    # 4️⃣ Lock funds from buyer wallet
    try:
        await Wallet.lock_balance(db, buyer_wallet.id, amount)
    except InsufficientFundsError:
        raise HTTPException(status_code=400, detail="Insufficient funds to lock")

    return {
        "message": "Funds locked successfully",
        "swap_id": swap.id,
        "buy_amount": amount,
        "pay_currency": pay_currency.value,
        "locked_amount": amount
    }

# 2️⃣ Confirm Swap Purchase (after payment confirmation)
@router.post("/buy/confirm/{swap_id}")
async def confirm_swap_purchase(
    swap_id: str,
    amount: Decimal,
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    # Get swap
    result = await db.execute(select(Swap).where(Swap.id == swap_id))
    swap: Swap = result.scalar_one_or_none()
    if not swap or swap.status in ["filled", "cancelled"]:
        raise HTTPException(status_code=400, detail="Swap not available")

    # Get buyer wallet
    result = await db.execute(
        select(Wallet).where(Wallet.user_id == user_id, Wallet.currency == swap.to_currency)
    )
    buyer_wallet: Wallet = result.scalar_one_or_none()

    if not buyer_wallet:
        raise HTTPException(status_code=400, detail="Buyer wallet not found")

    
    try:
        await Wallet.spend_locked_balance(db, buyer_wallet.id, amount)
    except InsufficientFundsError:
        raise HTTPException(status_code=400, detail="Insufficient locked balance")

    # Update swap remaining amount
    swap.remaining_amount -= amount
    swap.status = "filled" if swap.remaining_amount == 0 else "partial"
    db.add(swap)

    # Create buyer transaction
    tx_id = str(uuid4())
    buyer_tx = Transaction(
        id=tx_id,
        header="Swap Purchase",
        description=f"Bought {amount} {swap.to_currency} from {swap.creator_id} at rate {swap.rate}",
        from_user_id=user_id,
        to_user_id=swap.creator_id,
        type=TransactionType.BUY,
        status=TransactionStatus.COMPLETED,
        from_currency=swap.from_currency,
        to_currency=swap.to_currency,
        from_amount=amount,
        to_amount=amount,
        reference=str(uuid4())
    )
    db.add(buyer_tx)

    # Credit seller wallet
    result = await db.execute(
        select(Wallet).where(Wallet.user_id == swap.creator_id, Wallet.currency == swap.to_currency)
    )
    seller_wallet: Wallet = result.scalar_one_or_none()
    if not seller_wallet:
        raise HTTPException(status_code=400, detail="Seller wallet not found")
    seller_wallet.balance += amount
    db.add(seller_wallet)

    # Create SwapExecution
    execution = SwapExecution(
        id=str(uuid4()),
        swap_id=swap.id,
        taker_id=user_id,
        amount=amount,
        rate=swap.rate,
        from_currency=swap.from_currency,
        to_currency=swap.to_currency,
        transaction_id=tx_id,
        created_at=datetime.utcnow()
    )
    db.add(execution)

    await db.commit()
    await db.refresh(swap)

    return {"message": "Swap purchase confirmed", "swap": swap, "execution": execution}