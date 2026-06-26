import os
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Request, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from database import get_db
from utils.dependencies.auth import get_current_user
from decimal import Decimal
from sqlalchemy import func, case, select
import json
from models import Wallet, User, WalletType, Withdrawal, WithdrawalIntent, CurrencyType, WalletStatus, Transaction, TransactionHeader, TransactionStatus, TransactionType, LedgerEntry, DepositIntent, LedgerEntryType
from schemas import WalletResponse, DepositRequest
from dotenv import load_dotenv
from utils.flutterwave_apis import get_banks, verify_account, initiate_bank_transfer, charge_card, charge_ussd, create_virtual_account, charge_mobile_money
from typing import Optional
from utils.email_config import send_email
import logging

logger = logging.getLogger(__name__)
load_dotenv()

router = APIRouter(
    prefix="/api/v1",
    tags=["wallets"]
)






@router.get("/banks")
async def banks(
    country: str = "NG",
    user: User = Depends(get_current_user)):
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
    currency: str,
    user: User = Depends(get_current_user)
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
    result = await db.execute(
        select(Wallet).where(Wallet.user_id == user.id)
    )
    wallets = result.scalars().all()

    responses = []

    for wallet in wallets:
        # Aggregate ledger data + locked balance
        summary_result = await db.execute(
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
                
                func.count(LedgerEntry.id).label("transaction_count"),
                
                # === Add this for locked_balance ===
                func.coalesce(
                    func.sum(
                        case(
                            (LedgerEntry.entry_type == LedgerEntryType.LOCKED, LedgerEntry.amount),
                            else_=0
                        )
                    ), 0
                ).label("locked_balance")
            ).where(LedgerEntry.wallet_id == wallet.id)
        )

        summary = summary_result.first()

        responses.append(
            WalletResponse(
                id=wallet.id,
                user_id=wallet.user_id,
                currency=wallet.currency,
                wallet_type=wallet.wallet_type.value,
                status=wallet.status.value,
                balance=Decimal(summary.balance),
                locked_balance=Decimal(summary.locked_balance or 0),
                total_credit=Decimal(summary.total_credit),
                total_debit=Decimal(summary.total_debit),
                transaction_count=summary.transaction_count or 0,
                created_at=wallet.created_at
            )
        )

    return responses


@router.get("/deposit-intents/me")
async def get_my_deposit_intents(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 20,
):
    result = await db.execute(
        select(DepositIntent)
        .where(DepositIntent.user_id == user.id)
        .order_by(DepositIntent.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    return result.scalars().all()



@router.post("/deposit")
async def deposit(
    payload: DepositRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Find wallet matching selected currency
    wallet_result = await db.execute(
        select(Wallet).where(
            Wallet.user_id == user.id,
            Wallet.currency == payload.currency,
            Wallet.status == WalletStatus.ACTIVE
        )
    )

    wallet = wallet_result.scalar_one_or_none()

    if not wallet:
        raise HTTPException(
            status_code=404,
            detail=f"{payload.currency} wallet not found"
        )

    reference = f"DEP-{uuid4()}"

    intent = DepositIntent(
        id=str(uuid4()),
        user_id=user.id,
        wallet_id=wallet.id,
        amount=payload.amount,
        currency=payload.currency,
        method=payload.method,
        reference= reference,
        status=TransactionStatus.PENDING
    )

    db.add(intent)
    await db.commit()

    try:

        match payload.method:

            case "card":

                if not payload.card:
                    raise HTTPException(
                        400,
                        "card details required"
                    )

                response = await charge_card(
                    amount=payload.amount,
                    currency=payload.currency,
                    card=payload.card,
                    email=user.email,
                    reference=reference
                )

                return {
                    "method": "card",
                    "data": response
                }


            case "bank_transfer":

                response = await create_virtual_account(
                    amount=payload.amount,
                    currency=payload.currency,
                    email=user.email,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    country_code=user.country_code,
                    phone_number=user.phone_number,
                    reference=reference
                )

                return {
                    "method": "bank_transfer",
                    "data": response
                }

            case _:
                raise HTTPException(
                    400,
                    "unsupported deposit method"
                )

    except Exception:

        # payment setup failed
        intent.status = TransactionStatus.FAILED

        db.add(intent)
        await db.commit()

        raise


@router.post("/transfer")
async def transfer_funds(
    account_number: str,
    bank_code: str,
    currency: str,
    amount: float,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    reference = f"WTH-{uuid4()}"
    amount_dec = Decimal(str(amount))

    try:
        result = await db.execute(
            select(Wallet).where(
                Wallet.user_id == user.id,
                Wallet.currency == currency
            )
        )

        wallet = result.scalar_one_or_none()

        if not wallet:
            raise HTTPException(404, "Wallet not found")

        current_balance = wallet.balance or Decimal("0")
        current_locked = wallet.locked_balance or Decimal("0")
        available_balance = current_balance - current_locked

        if amount_dec <= 0:
            raise HTTPException(
                status_code=400,
                detail="Amount must be greater than zero"
            )

        if available_balance < amount_dec:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient balance. Available: {available_balance} {currency}"
            )

        # Lock funds
        await Wallet.lock_balance(
            db,
            wallet.id,
            amount_dec
        )

        intent = WithdrawalIntent(
            id=str(uuid4()),
            user_id=user.id,
            wallet_id=wallet.id,
            reference=reference,
            amount=amount_dec,
            currency=currency,
            account_number=account_number,
            bank_code=bank_code,
            status=TransactionStatus.PENDING
        )

        db.add(intent)
        await db.flush()

        try:
            transfer_response = await initiate_bank_transfer(
                account_number=account_number,
                bank_code=bank_code,
                amount=float(amount_dec),
                source_currency=currency,
                destination_currency=currency,
            )

            status = (
                transfer_response.get("status")
                or transfer_response.get("data", {}).get("status")
            )

            if str(status).lower() in [
                "success",
                "completed",
                "queued",
                "pending"
            ]:

               

                wallet.balance -= amount_dec
                wallet.locked_balance -= amount_dec

                intent.status = TransactionStatus.PROCESSING

                intent.provider_reference = (
                    transfer_response
                    .get("data", {})
                    .get("id")
                )

                await db.commit()

                return {
                    "status": "success",
                    "reference": reference,
                    "transfer_response": transfer_response,
                    "available_balance": float(
                        wallet.balance - wallet.locked_balance
                    )
                }

            else:
                raise Exception(
                    f"Transfer rejected: {transfer_response}"
                )

        except Exception as transfer_error:

            # Unlock funds
            wallet.locked_balance -= amount_dec

            intent.status = TransactionStatus.FAILED
            intent.failure_reason = str(transfer_error)

            await db.commit()

            raise HTTPException(
                status_code=400,
                detail=f"Transfer failed: {str(transfer_error)}"
            )

    except HTTPException:
        raise

    except Exception as e:
        await db.rollback()

        logger.exception(
            f"Withdrawal error for user {user.id}"
        )

        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )



async def process_deposit(
    db: AsyncSession,
    data: dict,
):
    reference = data.get("reference")
    amount = Decimal(str(data.get("amount", 0)))
    currency = data.get("currency")

    result = await db.execute(
        select(DepositIntent)
        .where(DepositIntent.reference == reference)
    )

    intent = result.scalar_one_or_none()

    if not intent:
        return {"message": "intent not found"}

    if intent.status == TransactionStatus.COMPLETED:
        return {"message": "already processed"}

    intent.status = TransactionStatus.COMPLETED
    intent.flutterwave_response = data

    tx = Transaction(
        id=str(uuid4()),
        header=TransactionHeader.WALLET_FUND.value,
        description="Wallet funding via Flutterwave",
        from_user_id=intent.user_id,
        to_user_id=intent.user_id,
        type=TransactionType.DEPOSIT,
        status=TransactionStatus.COMPLETED,
        from_currency=currency,
        to_currency=currency,
        from_amount=amount,
        to_amount=amount,
        reference=reference
    )

    db.add(tx)

    await db.flush()

    await Wallet.credit_wallet(
        db=db,
        wallet_id=intent.wallet_id,
        amount=amount,
        tx_id=tx.id
    )

    await db.commit()

    return {
        "status": "success",
        "message": "wallet credited"
    }



async def process_withdrawal(
    db,
    data: dict
):

    print(f"WITHDRAW DATA PROCESS:....: {data}")
    reference = data.get("reference")
    status = data.get("status")

    async with db.begin():

        result = await db.execute(
            select(Withdrawal)
            .where(
                Withdrawal.reference==reference
            )
        )

        withdrawal = (
            result.scalar_one_or_none()
        )

        if not withdrawal:
            return {
                "message":
                "withdrawal not found"
            }

        if withdrawal.status in [
            TransactionStatus.COMPLETED,
            TransactionStatus.FAILED
        ]:
            return {
                "message":
                "already processed"
            }

        wallet_result = await db.execute(
            select(Wallet)
            .where(
                Wallet.id==
                withdrawal.wallet_id
            )
            .with_for_update()
        )

        wallet = wallet_result.scalar_one()

        amount = Decimal(
            str(withdrawal.amount)
        )

        if status == "succeeded":

            wallet.locked_balance -= amount

            withdrawal.status = (
                TransactionStatus.COMPLETED
            )

            tx_status = (
                TransactionStatus.COMPLETED
            )

            print(
                "withdraw successful"
            )

        else:

            # unlock money
            wallet.locked_balance -= amount

            withdrawal.status = (
                TransactionStatus.FAILED
            )

            tx_status = (
                TransactionStatus.FAILED
            )

            print(
                "withdraw failed"
            )

        tx_result = await db.execute(
            select(Transaction)
            .where(
                Transaction.id==
                withdrawal.transaction_id
            )
        )

        tx = tx_result.scalar_one()

        tx.status = tx_status

    return {
        "message":
        "withdrawal processed"
    }



@router.post("/webhook/keta")
async def flutterwave_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):

    raw_body = await request.body()

    try:
        payload = json.loads(raw_body)
    except:
        raise HTTPException(400, "Invalid payload")

    signature = request.headers.get(
        "flutterwave-signature"
    )

    if not signature:
        raise HTTPException(
            401,
            "Missing webhook signature"
        )


    event_type = payload.get("type")
    data = payload.get("data", {})

    try:

        # Deposit webhook
        if event_type == "charge.completed":
            return await process_deposit(
                db,
                data
            )

        # Transfer webhook
        elif event_type == "transfer.completed":
            return await process_withdrawal(
                db,
                data
            )

        return {
            "message":"event ignored",
            "event":event_type
        }

    except Exception as e:
        print("WEBHOOK ERROR:", str(e))
        raise