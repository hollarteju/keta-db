import os
from tokenize import Token
import httpx
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select
from models import Wallet, User, WalletType, WalletStatus, Transaction, LedgerEntry
from database import get_db
from schemas import WalletResponse, VerifyAccountRequest, VerifyAccountResponse
import base64
from decimal import Decimal
from sqlalchemy import func, case
from utils.dependencies.auth import get_current_user
from models import User

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import Wallet, User, WalletType, CurrencyType, WalletStatus, Transaction, TransactionHeader, TransactionStatus, TransactionType
from database import get_db
from schemas import WalletResponse, FundWalletRequest, DevFundWalletRequest  # you'll define this schema for response
from uuid import uuid4
import requests
from dotenv import load_dotenv


load_dotenv()
FLUTTERWAVE_BASE_URL = "https://developersandbox-api.flutterwave.com"
FLUTTERWAVE_AUTH = "https://idp.flutterwave.com/realms/flutterwave/protocol/openid-connect/token"

router = APIRouter(
    prefix="/api/v1",
    tags=["wallets"]
)

def get_flutterwave_token():
    url = FLUTTERWAVE_AUTH
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = {
        "client_id": os.getenv("CLIENT_ID"),
        "client_secret": os.getenv("CLIENT_SECRET"),
        "grant_type": "client_credentials"
    }

    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status() 
        return response.json()

    except requests.exceptions.RequestException as e:
        return None

async def get_banks(country: str = "NG"):
    async with httpx.AsyncClient() as client:
        TOKEN = get_flutterwave_token()
        
        resp = await client.get(
            f"{FLUTTERWAVE_BASE_URL}/banks",
            params={"country": country},
            headers={
                "accept": "application/json",
                "Authorization": f"Bearer {TOKEN.get("access_token")}"
            }
        )
        data = resp.json()
    return data.get("data", [])

async def verify_account(account: str, bank_code: str, currency: str):
    async with httpx.AsyncClient() as client:
        token_data = get_flutterwave_token()
        access_token = token_data.get("access_token")

        payload = {
            "account": {
                "code": bank_code,
                "number": account
            },
            "currency": currency
        }

        resp = await client.post(
            f"{FLUTTERWAVE_BASE_URL}/banks/account-resolve",
            json=payload,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
        )
        return resp.json()

@router.get("/banks")
async def banks(country: str = "NG"):
    banks = await get_banks(country)
    return {
        "status": "success",
        "message": f"Banks fetched successfully for {country}",
        "data": banks
    }


@router.post("/account_lookup")
async def verify_account_number(
    account_number: str,
    bank_code: str,
    currency: str
):
    account = await verify_account(account_number, bank_code, currency)

    return {
        "status": "success",
        "message": "Account lookup completed",
        "data": account
    }



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



@router.get("/user", response_model=list[WalletResponse])
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
        print(summary._mapping.keys())
        responses.append(
            WalletResponse(
                id=wallet.id,
                user_id=wallet.user_id,
                currency=wallet.currency,
                wallet_type=wallet.wallet_type.value,
                status=wallet.status.value,
                balance=Decimal(summary.balance),
                # locked_balance=Decimal(summary.locked_balance),
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


