import os
import httpx
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select
from models import Wallet, User, WalletType, WalletStatus, Transaction, LedgerEntry
from database import get_db
from schemas import WalletResponse, FundWalletRequest, DevFundWalletRequest
import base64
from decimal import Decimal
from sqlalchemy import func, case
from utils.dependencies.auth import get_current_user
from models import User


MONNIFY_BASE_URL = "https://sandbox.monnify.com"


MONNIFY_API_KEY = os.getenv("MONNIFY_API_KEY")
MONNIFY_SECRET_KEY = os.getenv("MONNIFY_SECRET_KEY")
MONNIFY_CONTRACT_CODE = os.getenv("MONNIFY_CONTRACT_CODE")

router = APIRouter(
    prefix="/api/v1",
    tags=["wallets"]
)

async def get_monnify_token():
    auth_string = f"{MONNIFY_API_KEY}:{MONNIFY_SECRET_KEY}"
    encoded = base64.b64encode(auth_string.encode()).decode()

    headers = {
        "Authorization": f"Basic {encoded}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{MONNIFY_BASE_URL}/api/v1/auth/login",
            headers=headers
        )
        data = resp.json()

    if not data.get("requestSuccessful"):
        raise HTTPException(400, "Monnify authentication failed")

    return data["responseBody"]["accessToken"]


async def get_monnify_token() -> str:
    """Get Monnify Bearer token from API keys"""
    auth_string = f"{MONNIFY_API_KEY}:{MONNIFY_SECRET_KEY}"
    encoded = base64.b64encode(auth_string.encode()).decode()

    headers = {
        "Authorization": f"Basic {encoded}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{MONNIFY_BASE_URL}/api/v1/auth/login", headers=headers)
        data = resp.json()

    if not data.get("requestSuccessful"):
        raise Exception(f"Monnify authentication failed: {data.get('responseMessage')}")

    return data["responseBody"]["accessToken"]


async def monnify_initialize_payment(user_id: str, amount: float, payment_reference: str, token: str) -> str:
    """
    Initialize a Monnify payment and return checkout URL.
    Backend-only integration.
    """
    payload = {
        "amount": float(amount),
        "customerName": user_id,
        "customerEmail": f"{user_id}@example.com",  # you can fetch real email from DB
        "paymentReference": payment_reference,
        "contractCode": MONNIFY_CONTRACT_CODE,
        "currencyCode": "NGN",
        "paymentDescription": "Wallet funding",
        "redirectUrl": "https://yourfrontend.com/payment-success"  # frontend redirect after payment
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{MONNIFY_BASE_URL}/api/v1/merchant/transactions/init-transaction",
            json=payload,
            headers=headers
        )
        data = resp.json()

    if not data.get("requestSuccessful"):
        raise Exception(f"Monnify transaction initialization failed: {data.get('responseMessage')}")

    return data["responseBody"]["checkoutUrl"]


@router.post("/fund/initiate")
async def fund_wallet(user_id: str, currency: str, amount: Decimal, db: AsyncSession = Depends(get_db)):
    # 1️⃣ Create pending transaction
    tx = Transaction(
        id=str(uuid4()),
        header=TransactionHeader.WALLET_FUND.value,
        description="Wallet funding via Monnify",
        from_user_id=user_id,
        to_user_id=user_id,
        type=TransactionType.DEPOSIT,
        status=TransactionStatus.PENDING,
        from_currency=currency,
        to_currency=currency,
        from_amount=amount,
        to_amount=amount,
        reference=str(uuid4())
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx)

    # 2️⃣ Initialize Monnify payment (server-side)
    token = await get_monnify_token()
    checkout_url = await monnify_initialize_payment(user_id, amount, tx.reference, token)

    return {"transaction_id": tx.id, "checkout_url": checkout_url}


# @router.post("/fund/initiate")
# async def initiate_fund_wallet(request: FundWalletRequest, db: AsyncSession = Depends(get_db)):
#     result = await db.execute(select(Wallet).where(Wallet.user_id == request.user_id))
#     wallet = result.scalar_one_or_none()
#     if not wallet:
#         raise HTTPException(status_code=404, detail="Wallet not found")

#     reference = str(uuid4())

#     token = await get_monnify_token()

#     headers = {
#         "Authorization": f"Bearer {token}",
#         "Content-Type": "application/json"
#     }

#     payload = {
#         "amount": float(request.amount),
#         "customerName": request.user_id,
#         "customerEmail": f"{request.user_id}@example.com",
#         "paymentReference": reference,
#         "contractCode": MONNIFY_CONTRACT_CODE,
#         "currencyCode": "NGN",
#         "paymentDescription": "Wallet funding",
#         "redirectUrl": "https://yourfrontend.com/payment-success"
#     }

#     async with httpx.AsyncClient() as client:
#         resp = await client.post(
#             f"{MONNIFY_BASE_URL}/api/v1/merchant/transactions/init-transaction",
#             json=payload,
#             headers=headers
#         )
#         data = resp.json()

#     if not data.get("requestSuccessful"):
#         raise HTTPException(400, data.get("responseMessage"))

#     checkout_url = data["responseBody"]["checkoutUrl"]

#     # Save pending transaction
#     transaction = Transaction(
#         header="WALLET_FUND",
#         description="Wallet funding initiated",
#         from_user_id=request.user_id,
#         to_user_id=request.user_id,
#         type="DEPOSIT",
#         status="PENDING",
#         from_currency="NGN",
#         to_currency="NGN",
#         from_amount=request.amount,
#         to_amount=request.amount,
#         reference=reference
#     )

#     db.add(transaction)
#     await db.commit()

#     return {
#         "payment_url": checkout_url,
#         "reference": reference
#     }

# -------------------------------
# 2b. Monnify Webhook
# -------------------------------
@router.post("/monnify/webhook")
async def monnify_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.json()

    if payload.get("paymentStatus") != "PAID":
        return {"status": "ignored"}

    reference = payload.get("paymentReference")
    user_id = payload.get("customerName")
    amount_paid = float(payload.get("amountPaid") or payload.get("amount"))

    # find transaction
    result = await db.execute(
        select(Transaction).where(Transaction.reference == reference)
    )
    transaction = result.scalar_one_or_none()

    if not transaction or transaction.status == "COMPLETED":
        return {"status": "already_processed"}

    result = await db.execute(select(Wallet).where(Wallet.user_id == user_id))
    wallet = result.scalar_one_or_none()

    if not wallet:
        raise HTTPException(404, "Wallet not found")

    wallet.balance += amount_paid
    transaction.status = "COMPLETED"

    db.add(wallet)
    db.add(transaction)
    await db.commit()

    return {"status": "wallet_credited"}


from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import Wallet, User, WalletType, CurrencyType, WalletStatus, Transaction, TransactionHeader, TransactionStatus, TransactionType
from database import get_db
from schemas import WalletResponse, FundWalletRequest  # you'll define this schema for response
from uuid import uuid4

# router = APIRouter(
#     prefix="/api/v1",
#     tags=["wallets"]
# )

@router.post("/create", response_model=WalletResponse)
async def create_wallet(
    user: User = Depends(get_current_user),
    currency: CurrencyType = CurrencyType.DOLLAR,  # default currency is NGN
    wallet_type: WalletType = WalletType.FIAT,  # default type is FIAT
    db: AsyncSession = Depends(get_db)
):

    result = await db.execute(
    select(Wallet).where(
        Wallet.user_id == user.id,
        Wallet.currency == currency
    )
)
    existing_wallet = result.scalar_one_or_none()
    if existing_wallet:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{currency} wallet already exists for this user"
        )

    # 3️⃣ Create new wallet
    new_wallet = Wallet(
        user_id=user.id,
        currency=currency.value,
        wallet_type=wallet_type,
        status=WalletStatus.ACTIVE
    )

    try:
        db.add(new_wallet)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"{currency} wallet already exists for this user"
        )
    return WalletResponse(
    id=new_wallet.id,
    user_id=new_wallet.user_id,
    currency=new_wallet.currency,
    wallet_type=new_wallet.wallet_type.value,
    status=new_wallet.status.value,
    balance=0,              # new wallet, no transactions yet
    total_credit=0,
    total_debit=0,
    transaction_count=0,
    created_at=new_wallet.created_at
)



@router.get("/user/{user_id}", response_model=list[WalletResponse])
async def get_user_wallets(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 1️⃣ Ensure user exists
    
    result = await db.execute(
        select(Wallet).where(Wallet.user_id == user.id)
    )
    wallets = result.scalars().all()

    responses = []

    for wallet in wallets:
        # 3️⃣ Aggregate ledger data
        result = await db.execute(
            select(
                func.coalesce(func.sum(LedgerEntry.amount), 0).label("balance"),
                func.coalesce(
                    func.sum(
                        case(
                            (LedgerEntry.amount > 0, LedgerEntry.amount),
                            else_=0
                        )
                    ), 0
                ).label("total_credit"),
                func.coalesce(
                    func.sum(
                        case(
                            (LedgerEntry.amount < 0, -LedgerEntry.amount),
                            else_=0
                        )
                    ), 0
                ).label("total_debit"),
                func.count(LedgerEntry.id).label("transaction_count")
            ).where(LedgerEntry.wallet_id == wallet.id)
        )

        summary = result.first()

        responses.append(
            WalletResponse(
                id=wallet.id,
                user_id=wallet.user_id,
                currency=wallet.currency,
                wallet_type=wallet.wallet_type.value,
                status=wallet.status.value,
                balance=Decimal(summary.balance),
                total_credit=Decimal(summary.total_credit),
                total_debit=Decimal(summary.total_debit),
                transaction_count=summary.transaction_count,
                created_at=wallet.created_at
            )
        )

    return responses


@router.post("/fund")
async def dev_fund_wallet(
    request: DevFundWalletRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 1️⃣ Find wallet
    result = await db.execute(
        select(Wallet).where(
            Wallet.user_id == user.id,
            Wallet.currency == request.currency
        )
    )
    wallet = result.scalar_one_or_none()

    if not wallet:
        raise HTTPException(
            status_code=404,
            detail=f"{request.currency} wallet not found"
        )

    if wallet.status != WalletStatus.ACTIVE:
        raise HTTPException(
            status_code=400,
            detail="Wallet is frozen"
        )

    # 2️⃣ Create completed transaction
    tx_id = str(uuid4())

    transaction = Transaction(
        id=tx_id,
        header=TransactionHeader.WALLET_FUND.value,
        description="DEV wallet funding",
        from_user_id=user.id,
        to_user_id=user.id,
        type=TransactionType.DEPOSIT,
        status=TransactionStatus.COMPLETED,
        from_currency=request.currency,
        to_currency=request.currency,
        from_amount=request.amount,
        to_amount=request.amount,
        reference=f"DEV-{uuid4()}"
    )

    db.add(transaction)

    # 3️⃣ Credit wallet using ledger
    await Wallet.credit_wallet(
        db=db,
        wallet_id=wallet.id,
        amount=request.amount,
        tx_id=tx_id
    )


    wallet.balance = (wallet.balance or 0) + request.amount

    await db.commit()
    await db.refresh(wallet)

    balance = await Wallet.get_wallet_balance(db, wallet.id)

    return {
        "message": "Wallet funded (development mode)",
        "wallet_id": wallet.id,
        "credited_amount": request.amount,
        "current_balance": balance
    }
