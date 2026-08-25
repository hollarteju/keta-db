from utils.websocket_manager import manager
from sqlalchemy.orm import selectinload
from datetime import datetime
from uuid import uuid4
from utils.rates import fetch_currency_rates
from models import Wallet, SwapBid, Swap_bidstatus
from schemas import SwapCreate, SwapUpdate, BuyerBidUpdate
from fastapi import APIRouter, Depends, HTTPException, Query,  WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from decimal import Decimal

from database import get_db
from utils.dependencies.auth import get_current_user
from models import Swap, Wallet, SwapStatus, Transaction, TransactionType, TransactionStatus, SwapExecution, InsufficientFundsError, LedgerEntryType, User, NotificationType
from utils.notification import create_notification


def serialize_swap(swap: Swap) -> dict:
    return {
        "id": str(swap.id),
        "creator_id": str(swap.creator_id),
        "from_currency": swap.from_currency,
        "to_currency": swap.to_currency,
        "amount": float(swap.amount),
        "remaining_amount": float(swap.remaining_amount),
        "min_amount": float(swap.min_amount),
        "rate": float(swap.rate),
        "status": swap.status.value,
        "expires_at": (
            swap.expires_at.isoformat()
            if swap.expires_at
            else None
        ),
        "created_at": (
            swap.created_at.isoformat()
            if swap.created_at
            else None
        )
    }


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

    await manager.broadcast_market({
        "event": "swap_created",
        "swap": serialize_swap(swap)
    })

    return swap


@router.get("/")
async def get_all_swaps(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):

    result = await db.execute(
        select(Swap)
        .options(selectinload(Swap.creator))
        .where(Swap.status == SwapStatus.OPEN)
    )

    swaps = result.scalars().all()

    return [
        {
            "id": swap.id,
            "wallet_id": swap.wallet_id,
            "from_currency": swap.from_currency,
            "to_currency": swap.to_currency,
            "amount": swap.amount,
            "min_amount": swap.min_amount,
            "remaining_amount": swap.remaining_amount,
            "rate": swap.rate,
            "expires_at": swap.expires_at,
            "status": swap.status,

            # 👇 key part
            "creator_name": "you" if swap.creator_id == user.id else swap.creator.full_name
        }
        for swap in swaps
    ]


@router.get("/me")
async def get_user_swaps(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):

    result = await db.execute(
        select(Swap).where(Swap.creator_id == user.id)
    )

    swaps = result.scalars().all()

    return swaps


@router.get("/creator/bids")
async def get_creator_bids(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(SwapBid)
        .join(Swap, Swap.id == SwapBid.swap_id)
        .where(
            Swap.creator_id == user.id
        )
        .order_by(SwapBid.created_at.desc())
    )

    bids = result.scalars().all()

    return {
        "message": "Creator bids retrieved successfully",
        "count": len(bids),
        "bids": bids
    }


@router.patch("/{swap_id}")
async def update_swap(
    swap_id: str,
    data: SwapUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Swap).where(Swap.id == swap_id)
    )

    swap = result.scalar_one_or_none()

    if not swap:
        raise HTTPException(404, "Swap not found")

    if swap.creator_id != user.id:
        raise HTTPException(403, "You are not the owner of this swap")

    changed_fields = []

    if data.rate is not None and data.rate != swap.rate:
        swap.rate = data.rate
        changed_fields.append("rate")

    if data.expires_at is not None and data.expires_at != swap.expires_at:
        swap.expires_at = data.expires_at
        changed_fields.append("expiration")

    if not changed_fields:
        return swap

    db.add(swap)

    # Get all buyers with active purchase intents
    result = await db.execute(
        select(SwapBid).where(
            SwapBid.swap_id == swap.id,
            SwapBid.status == Swap_bidstatus.ACTIVE
        )
    )

    active_bids = result.scalars().all()

    await db.commit()
    await db.refresh(swap)

    # Notify buyers
    for bid in active_bids:
        buyers_notification = await create_notification(
            user_id=bid.buyer_id,
            type=NotificationType.SYSTEM,
            title="Swap Updated",
            message=(
                f"The swap you have an active purchase intent on "
                f"has been updated."
            ),
            reference_id=swap.id,
        )

        db.add(buyers_notification)

    await db.commit()

    await manager.broadcast_market(
        {
            "event": "swap_updated",
            "swap": serialize_swap(swap),
        }
    )

    return swap


@router.delete("/{swap_id}")
async def cancel_swap(
    swap_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Swap).where(Swap.id == swap_id)
    )

    swap = result.scalar_one_or_none()

    if not swap:
        raise HTTPException(404, "Swap not found")

    if swap.creator_id != user.id:
        raise HTTPException(403, "You are not the owner of this swap")

    if swap.status != SwapStatus.OPEN:
        raise HTTPException(
            400,
            "Swap cannot be cancelled"
        )

    # Get all active buyer intents
    result = await db.execute(
        select(SwapBid).where(
            SwapBid.swap_id == swap.id,
            SwapBid.status == Swap_bidstatus.ACTIVE
        )
    )

    active_bids = result.scalars().all()

    try:
        # Unlock seller's remaining funds
        if swap.remaining_amount > 0:
            await Wallet.unlock_balance(
                db,
                swap.wallet_id,
                swap.remaining_amount
            )

        # Unlock all buyers' locked payment funds
        for bid in active_bids:
            await Wallet.unlock_balance(
                db,
                bid.buyer_wallet_id,
                bid.locked_amount
            )

            bid.status = Swap_bidstatus.CANCELLED
            db.add(bid)

        # Cancel swap
        swap.status = SwapStatus.CANCELLED
        db.add(swap)

        await db.commit()

    except Exception:
        await db.rollback()
        raise

    # Notify buyers after successful transaction
    for bid in active_bids:
        notification = await create_notification(
            user_id=bid.buyer_id,
            type=NotificationType.SYSTEM,
            title="Swap Cancelled",
            message=(
                "The swap you created a purchase intent for "
                "has been cancelled. Your locked funds have been released."
            ),
            reference_id=swap.id,
        )

        db.add(notification)

    await db.commit()

    await manager.broadcast_market(
        {
            "event": "swap_deleted",
            "swap": serialize_swap(swap),
        }
    )

    return {
        "message": "Swap cancelled",
    }


@router.post("/buy/intent/{swap_id}")
async def initiate_swap_purchase(
    swap_id: str,
    wallet_id: str,
    amount: Decimal = Query(..., description="Amount of swap currency to buy"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Swap).where(Swap.id == swap_id))
    swap: Swap = result.scalar_one_or_none()
    if not swap or swap.status in ["filled", "cancelled"]:
        raise HTTPException(status_code=400, detail="Swap not available")

    if not swap.validate_order_amount(amount):
        raise HTTPException(status_code=401, detail="Invalid trade amount")
    result = await db.execute(select(Wallet).where(Wallet.user_id == user.id,  Wallet.id == wallet_id))
    buyer_wallet: Wallet = result.scalar_one_or_none()
    if not buyer_wallet:
        raise HTTPException(
            status_code=400, detail=f"Buyer wallet not found for {buyer_wallet.currency}")

    try:
        locked_balance = swap.rate * amount
        await Wallet.lock_balance(db, buyer_wallet.id, locked_balance)

        bid = SwapBid(
            swap_id=swap.id,
            buyer_id=user.id,
            buyer_wallet_id=buyer_wallet.id,
            bid_rate=swap.rate,
            amount=amount,
            locked_amount=locked_balance,
            status=Swap_bidstatus.ACTIVE,
        )

        db.add(bid)

        await db.commit()
        await db.refresh(bid)

    except InsufficientFundsError:
        raise HTTPException(
            status_code=400, detail="Insufficient funds to lock")

    return {
        "message": "Funds locked successfully",
        "swap_id": swap.id,
        "buy_amount": amount,
        "pay_currency": buyer_wallet.currency,
        "locked_amount": locked_balance
    }


@router.post("/buy/confirm/{swap_id}")
async def confirm_swap_purchase(
    swap_id: str,
    swapBid_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):

    tx_id = str(uuid4())
    result = await db.execute(
        select(Swap).where(Swap.id == swap_id)
    )

    swap = result.scalar_one_or_none()

    if not swap or swap.status in [
        SwapStatus.FILLED,
        SwapStatus.CANCELLED
    ]:
        raise HTTPException(
            status_code=400,
            detail="Swap not available"
        )

    # Get buyer's active bid
    result = await db.execute(
        select(SwapBid).where(
            SwapBid.id == swapBid_id,
            SwapBid.swap_id == swap.id,
            SwapBid.status == Swap_bidstatus.ACTIVE
        )
    )

    bid = result.scalar_one_or_none()

    if not bid:
        raise HTTPException(
            status_code=400,
            detail="No active purchase intent found"
        )

    if swap.creator_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="Only the swap owner can confirm a purchase intent"
        )

    # Make sure swap still has enough quantity
    if bid.amount > swap.remaining_amount:
        raise HTTPException(
            status_code=400,
            detail="Requested amount exceeds available swap amount"
        )

    try:
        # select vendor wallet
        result = await db.execute(
            select(Wallet).where(
                Wallet.user_id == swap.creator_id,
                Wallet.currency == swap.to_currency
            )
        )

        seller_wallet = result.scalar_one_or_none()

        if not seller_wallet:
            raise HTTPException(
                status_code=400,
                detail="Seller wallet not found"
            )

        # select bidder wallet
        bidder = await db.execute(
            select(Wallet).where(
                Wallet.user_id == bid.buyer_id,
                Wallet.currency == swap.from_currency
            )
        )

        bidder_wallet = bidder.scalar_one_or_none()

        if not bidder_wallet:
            raise HTTPException(
                status_code=400,
                detail="Seller wallet not found"
            )

        transaction_tx = Transaction(
                    header="Swap Sold",
                    description=(
                        f"Bought {bid.amount} {swap.to_currency} "
                        f"from {swap.creator_id} "
                        f"at rate {bid.bid_rate}"
                    ),
                    from_user_id=bid.buyer_id,
                    to_user_id=swap.creator_id,
                    type=TransactionType.BUY,
                    status=TransactionStatus.COMPLETED,
                    from_currency=swap.from_currency,
                    to_currency=swap.to_currency,
                    from_amount=bid.locked_amount,
                    to_amount=bid.amount,
                    reference=tx_id
                )

        db.add(transaction_tx)
        await db.flush()
        

        # spend vendor locked amount
        await Wallet.spend_locked_balance(
            db,
            swap.wallet_id,
            bid.amount
        )

        
        await Wallet.debit_wallet(
            db=db,
            wallet_id=swap.wallet_id,
            amount=bid.amount,
            tx_id=transaction_tx.id,
            entry_type=LedgerEntryType.SELL
        )

        # credit vendor balance amount
        await Wallet.credit_wallet(
            db=db,
            wallet_id=seller_wallet.id,
            amount=bid.amount * bid.bid_rate,
            tx_id=transaction_tx.id,
            entry_type=LedgerEntryType.BUY
        )

        # spend bidder locked amount
        await Wallet.spend_locked_balance(
            db,
            bid.buyer_wallet_id,
            bid.locked_amount
        )

        await Wallet.debit_wallet(
            db=db,
            wallet_id=bid.buyer_wallet_id,
            amount=bid.locked_amount,
            tx_id=transaction_tx.id,
            entry_type=LedgerEntryType.SELL
        )
        # spend vendor locked amount
        await Wallet.credit_wallet(
            db=db,
            wallet_id=bidder_wallet.id,
            amount=bid.amount,
            tx_id=transaction_tx.id,
            entry_type=LedgerEntryType.BUY
        )

        swap.remaining_amount -= bid.amount

        if swap.remaining_amount == 0:
            swap.status = SwapStatus.FILLED
        else:
            swap.status = SwapStatus.PARTIAL

        db.add(swap)

        # Mark confirmed bid as filled
        bid.status = Swap_bidstatus.EXECUTED
        db.add(bid)

        # Create transaction

        # Create execution
        execution = SwapExecution(
            swap_id=swap.id,
            taker_id=bid.buyer_id,
            amount=bid.amount,
            rate=bid.bid_rate,
            from_currency=swap.from_currency,
            to_currency=swap.to_currency,
            transaction_id=transaction_tx.id,
            created_at=datetime.utcnow()
        )

        db.add(execution)

        # --------------------------------------------------
        # RELEASE INVALID ACTIVE BUYER BIDS
        # --------------------------------------------------

        result = await db.execute(
            select(SwapBid).where(
                SwapBid.swap_id == swap.id,
                SwapBid.status == Swap_bidstatus.ACTIVE,
                SwapBid.id != bid.id
            )
        )

        active_bids = result.scalars().all()

        released_bids = []

        for other_bid in active_bids:

            # The buyer requested more than what
            # remains available in the swap.
            if other_bid.amount > swap.remaining_amount:

                await Wallet.unlock_balance(
                    db,
                    other_bid.buyer_wallet_id,
                    other_bid.locked_amount
                )

                other_bid.status = Swap_bidstatus.CANCELLED

                db.add(other_bid)

                released_bids.append(other_bid)

        await db.commit()
        await db.refresh(swap)

    except InsufficientFundsError:
        await db.rollback()

        raise HTTPException(
            status_code=400,
            detail="Insufficient locked balance"
        )

    except Exception:
        await db.rollback()
        raise

    # --------------------------------------------------
    # NOTIFICATIONS
    # --------------------------------------------------

    # Buyer who completed the purchase
    await create_notification(
        db,
        user_id=user.id,
        notification_type=NotificationType.SWAP,
        title="Swap Purchase Successful",
        message=(
            f"You successfully bought "
            f"{bid.amount} {swap.to_currency} "
            f"at a rate of {bid.bid_rate}."
        ),
        reference_id=tx_id,
        reference_type="transaction",
        extra_data={
            "swap_id": str(swap.id),
            "bid_id": str(bid.id),
            "role": "buyer",
        },
    )

    # Seller
    await create_notification(
        db,
        user_id=swap.creator_id,
        notification_type=NotificationType.SWAP,
        title="Your Swap Was Purchased",
        message=(
            f"{bid.amount} {swap.to_currency} "
            f"from your swap was purchased."
        ),
        reference_id=tx_id,
        reference_type="transaction",
        extra_data={
            "swap_id": str(swap.id),
            "bid_id": str(bid.id),
            "role": "seller",
        },
    )

    # Notify buyers whose bids were released
    for released_bid in released_bids:

        await create_notification(
            db,
            user_id=released_bid.buyer_id,
            notification_type=NotificationType.SWAP,
            title="Swap Purchase Intent Cancelled",
            message=(
                "Your purchase intent could no longer be fulfilled "
                "because the remaining swap amount was insufficient. "
                "Your locked funds have been released."
            ),
            reference_id=str(swap.id),
            reference_type="swap",
            extra_data={
                "swap_id": str(swap.id),
                "bid_id": str(released_bid.id),
                "role": "buyer",
                "locked_amount_released": str(
                    released_bid.locked_amount
                ),
            },
        )

    await db.commit()

    await manager.broadcast_market(
        {
            "event": "swap_completed",
            "swap": serialize_swap(swap)
        }
    )

    return {
        "message": "Swap purchase confirmed",
        "swap_id": swap.id,
        "bid_id": bid.id,
        "amount": bid.amount,
        "rate": bid.bid_rate,
        "locked_amount": bid.locked_amount,
        "released_bids": len(released_bids),
        "status": bid.status.value
    }


# # 2️⃣ Confirm Swap Purchase (after payment confirmation)
# @router.post("/buy/confirm/{swap_id}")
# async def confirm_swap_purchase(
#     swap_id: str,
#     amount: Decimal,
#     user_id: str,
#     db: AsyncSession = Depends(get_db)
# ):
#     # Get swap
#     result = await db.execute(select(Swap).where(Swap.id == swap_id))
#     swap: Swap = result.scalar_one_or_none()
#     if not swap or swap.status in ["filled", "cancelled"]:
#         raise HTTPException(status_code=400, detail="Swap not available")

#     # Get buyer wallet
#     result = await db.execute(
#         select(Wallet).where(Wallet.user_id == user_id,
#                              Wallet.currency == swap.to_currency)
#     )
#     buyer_wallet: Wallet = result.scalar_one_or_none()

#     if not buyer_wallet:
#         raise HTTPException(status_code=400, detail="Buyer wallet not found")

#     try:
#         await Wallet.spend_locked_balance(db, buyer_wallet.id, amount)
#     except InsufficientFundsError:
#         raise HTTPException(
#             status_code=400, detail="Insufficient locked balance")

#     # Update swap remaining amount
#     swap.remaining_amount -= amount
#     swap.status = "filled" if swap.remaining_amount == 0 else "partial"
#     db.add(swap)

#     # Create buyer transaction
#     tx_id = str(uuid4())
#     buyer_tx = Transaction(
#         id=tx_id,
#         header="Swap Purchase",
#         description=f"Bought {amount} {swap.to_currency} from {swap.creator_id} at rate {swap.rate}",
#         from_user_id=user_id,
#         to_user_id=swap.creator_id,
#         type=TransactionType.BUY,
#         status=TransactionStatus.COMPLETED,
#         from_currency=swap.from_currency,
#         to_currency=swap.to_currency,
#         from_amount=amount,
#         to_amount=amount,
#         reference=str(uuid4())
#     )
#     db.add(buyer_tx)

#     # Credit seller wallet
#     result = await db.execute(
#         select(Wallet).where(Wallet.user_id == swap.creator_id,
#                              Wallet.currency == swap.to_currency)
#     )
#     seller_wallet: Wallet = result.scalar_one_or_none()
#     if not seller_wallet:
#         raise HTTPException(status_code=400, detail="Seller wallet not found")
#     seller_wallet.balance += amount
#     db.add(seller_wallet)

#     # Create SwapExecution
#     execution = SwapExecution(
#         id=str(uuid4()),
#         swap_id=swap.id,
#         taker_id=user_id,
#         amount=amount,
#         rate=swap.rate,
#         from_currency=swap.from_currency,
#         to_currency=swap.to_currency,
#         transaction_id=tx_id,
#         created_at=datetime.utcnow()
#     )
#     db.add(execution)


#     await create_notification(
#     db,
#     user_id=user_id,
#     notification_type=NotificationType.SWAP,
#     title="Swap Purchase Successful",
#     message=f"You successfully bought {amount} {swap.to_currency}.",
#     reference_id=tx_id,
#     reference_type="transaction",
#     extra_data={
#         "swap_id": str(swap.id),
#         "role": "buyer",
#     },
# )

#     await create_notification(
#     db,
#     user_id=swap.creator_id,
#     notification_type=NotificationType.SWAP,
#     title="Your Swap Was Purchased",
#     message=f"{amount} {swap.to_currency} from your swap was purchased.",
#     reference_id=tx_id,
#     reference_type="transaction",
#     extra_data={
#         "swap_id": str(swap.id),
#         "role": "seller",
#     },
#     )

#     await db.commit()
#     await db.refresh(swap)

#     {
#         "event": "swap_completed",
#         "swap": {
#             "id": str(swap.id),
#             "remaining_amount": float(swap.remaining_amount),
#             "from_currency": swap.from_currency,
#             "to_currency": swap.to_currency,
#             "created_at": swap.created_at.isoformat() if swap.created_at else None,
#             "buyer_name": f"{swap.creator.first_name} {swap.creator.last_name}"

#         }
#     }

#     return {"message": "Swap purchase confirmed", "swap": swap, "execution": execution}
