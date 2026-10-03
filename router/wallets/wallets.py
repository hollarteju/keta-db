from datetime import datetime, timedelta
import os
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Request, status, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from database import get_db
from utils.dependencies.auth import get_current_user
from decimal import Decimal
from sqlalchemy import func, case, select
import json
from models import Wallet, User, WalletType, Withdrawal, TransactionDevice, Settings, WithdrawalIntent, CurrencyType, WalletStatus, Transaction, TransactionHeader, TransactionStatus, TransactionType, LedgerEntry, DepositIntent, LedgerEntryType
from schemas import WalletResponse, DepositRequest, CardPinRequest, TransactionPinCreateRequest, TransactionPinSetupRequest, TransactionPinVerifyRequest, WithdrawalAuthorizationRequest
from dotenv import load_dotenv
from utils.flutterwave_apis import get_banks, verify_account, initiate_bank_transfer, charge_card, authorize_charge_pin, create_virtual_account, charge_mobile_money
from typing import Optional
from utils.email_config import send_email
import logging
from utils.transaction_signature import verify_ed25519_signature
from utils.websocket_manager import manager
from secrets import token_urlsafe
from base64 import b64decode

from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey

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
                    customer=user,
                    card=payload.card,
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

    except Exception as e:

        # payment setup failed
        intent.status = TransactionStatus.FAILED

        db.add(intent)
        await db.commit()

        raise HTTPException( status_code=500, detail=f"Deposit failed" )


@router.post("/device-registration")
async def device_registration(
    data: TransactionPinSetupRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_id = str(current_user.id)

    try:
        result = await db.execute(
            select(TransactionDevice).where(
                TransactionDevice.user_id == user_id,
                TransactionDevice.device_id == data.device_id,
            )
        )

        existing_device = result.scalar_one_or_none()

        if existing_device:
            existing_device.device_name = data.device_name
            existing_device.public_key = data.public_key

            if existing_device.status == "REVOKED":
                existing_device.status = "ACTIVE"
                existing_device.revoked_at = None

            await db.commit()

            return {
                "message": "Transaction device synchronized successfully.",
                "device_id": existing_device.device_id,
                "status": existing_device.status,
            }

        device = TransactionDevice(
            id=str(uuid4()),
            user_id=user_id,
            device_id=data.device_id,
            device_name=data.device_name,
            public_key=data.public_key,
            status="ACTIVE",
        )

        db.add(device)

        await db.commit()

        return {
            "message": "Transaction device registered successfully.",
            "device_id": device.device_id,
            "status": "ACTIVE",
        }

    except HTTPException:
        await db.rollback()
        raise

    except Exception:
        await db.rollback()

        logger.exception(
            f"Transaction device registration error for user {user_id}"
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to register transaction device.",
        )

    

@router.post("/transaction-pin")
async def create_transaction_pin(
    data: TransactionPinCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_id = str(current_user.id)

    try:
        # --------------------------------------------------
        # 1. Get account settings
        # --------------------------------------------------
        settings_result = await db.execute(
            select(Settings).where(
                Settings.user_id == user_id
            )
        )

        settings = settings_result.scalar_one_or_none()

        if not settings:
            raise HTTPException(
                status_code=404,
                detail="User settings not found.",
            )

        # --------------------------------------------------
        # 2. Verify that this device belongs to the user
        #    and is active
        # --------------------------------------------------
        device_result = await db.execute(
            select(TransactionDevice).where(
                TransactionDevice.user_id == user_id,
                TransactionDevice.device_id == data.device_id,
                TransactionDevice.status == "ACTIVE",
            )
        )

        device = device_result.scalar_one_or_none()
      
        if not device:
            raise HTTPException(
                status_code=403,
                detail=(
                    "This device is not registered or "
                    "is not active for transaction security."
                ),
            )

        # --------------------------------------------------
        # 3. Validate PIN
        # --------------------------------------------------
        if not Settings.is_valid_pin(
            data.transaction_pin
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Transaction PIN must contain "
                    "exactly 4 digits."
                ),
            )
       

        # --------------------------------------------------
        # 5. Hash and store PIN
        # --------------------------------------------------
        settings.transaction_pin_hash = (
            Settings.hash_pin(
                data.transaction_pin
            )
        )

        settings.transaction_pin_enabled = True
        settings.transaction_pin_changed_at = (
            datetime.utcnow()
        )

        # Track device usage
        device.last_used_at = datetime.utcnow()

        await db.commit()

        return {
            "message": (
                "Transaction PIN created successfully"
            ),
            "enabled": True,
            "device_id": device.device_id,
        }

    except HTTPException:
        await db.rollback()
        raise

    except Exception as e:
        await db.rollback()

        logger.exception(
            "Transaction PIN creation error "
            f"for user {user_id}"
        )

        raise HTTPException(
            status_code=500,
            detail=f"Unable to create transaction PIN. {e}",
        )    


@router.post("/transaction-pin/verify")
async def verify_transaction_pin(
    data: TransactionPinVerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 1. Get the user's active transaction device
    result = await db.execute(
        select(TransactionDevice).where(
            TransactionDevice.user_id == current_user.id,
            TransactionDevice.device_id == data.device_id,
            TransactionDevice.status == "ACTIVE",
        )
    )

    device = result.scalar_one_or_none()

    if not device:
        raise HTTPException(
            status_code=404,
            detail="Active transaction device not found",
        )

    # 2. Validate timestamp to prevent replay attacks
    now = int(datetime.utcnow().timestamp())

    if abs(now - data.timestamp) > 60:
        raise HTTPException(
            status_code=400,
            detail="Transaction authorization has expired",
        )

    # 3. Reconstruct the exact message
    message = (
        f"transaction_id:{data.transaction_id}"
        f"|amount:{data.amount}"
        f"|currency:{data.currency}"
        f"|timestamp:{data.timestamp}"
    )

    # 4. Verify Ed25519 signature
    is_valid = verify_ed25519_signature(
        public_key_base64=device.public_key,
        signature_base64=data.signature,
        message=message,
    )

    if not is_valid:
        raise HTTPException(
            status_code=401,
            detail="Invalid transaction authorization",
        )

    return {
        "message": "Transaction PIN verified successfully",
        "verified": True,
    }



@router.post("/transfer/{withdrawal_id}/authorize")
async def authorize_withdrawal(
    withdrawal_id: str,
    payload: WithdrawalAuthorizationRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    user_id = str(user.id)

    try:
        # 1. Find withdrawal belonging to current user
        result = await db.execute(
            select(WithdrawalIntent)
            .where(
                WithdrawalIntent.id == withdrawal_id,
                WithdrawalIntent.user_id == user_id,
            )
            .with_for_update()
        )

        withdrawal = result.scalar_one_or_none()

        if not withdrawal:
            raise HTTPException(
                status_code=404,
                detail="Withdrawal not found",
            )

        # 2. Must still be pending verification
        if withdrawal.status != TransactionStatus.PENDING:
            raise HTTPException(
                status_code=400,
                detail="Withdrawal is not awaiting authorization.",
            )

        # 3. Challenge must exist
        if not withdrawal.challenge:
            raise HTTPException(
                status_code=400,
                detail="Withdrawal challenge not found.",
            )

        # 4. Challenge must not have been used
        if withdrawal.challenge_used_at:
            raise HTTPException(
                status_code=400,
                detail="Withdrawal challenge has already been used.",
            )

        # 5. Challenge must not be expired
        if (
            not withdrawal.challenge_expires_at
            or datetime.utcnow()
            > withdrawal.challenge_expires_at
        ):
            withdrawal.status = TransactionStatus.FAILED

            wallet_result = await db.execute(
                select(Wallet)
                .where(
                    Wallet.id == withdrawal.wallet_id
                )
                .with_for_update()
            )

            wallet = wallet_result.scalar_one()

            amount = Decimal(
                str(withdrawal.amount)
            )

            wallet.locked_balance -= amount

            await db.commit()

            raise HTTPException(
                status_code=400,
                detail="Withdrawal authorization has expired.",
            )

        # 6. Find registered transaction device
        device_result = await db.execute(
            select(TransactionDevice)
            .where(
                TransactionDevice.device_id
                == payload.device_id,
                TransactionDevice.user_id
                == user_id,
            )
        )

        device = device_result.scalar_one_or_none()

        if not device:
            raise HTTPException(
                status_code=403,
                detail="Transaction device not registered.",
            )

        # Get settings
        settings_result = await db.execute(
            select(Settings).where(
                Settings.user_id == user_id
            )
        )

        settings = settings_result.scalar_one_or_none()

        if not settings:
            raise HTTPException(
                status_code=404,
                detail="User settings not found.",
            )

        if not settings.transaction_pin_enabled:
            raise HTTPException(
                status_code=400,
                detail="Transaction PIN is not enabled.",
            )

        if not settings.verify_pin(
            payload.transaction_pin
        ):
            raise HTTPException(
                status_code=401,
                detail="Invalid transaction PIN.",
            )
        
        try:
            public_key = b64decode(
                device.public_key
            )

            signature = b64decode(
                payload.signature
            )

        except Exception:
            raise HTTPException(
                status_code=400,
                detail="Invalid signature encoding.",
            )

        # 9. Verify Ed25519 signature
        try:
            verify_key = VerifyKey(public_key)

            verify_key.verify(
                withdrawal.challenge.encode("utf-8"),
                signature,
            )

        except BadSignatureError:
            raise HTTPException(
                status_code=401,
                detail="Invalid transaction signature.",
            )

        # 10. Mark challenge as used
        withdrawal.challenge_used_at = datetime.utcnow()

        withdrawal.transaction_device_id = device.id

        # 11. Find transaction
        tx_result = await db.execute(
            select(Transaction).where(
                Transaction.reference
                == withdrawal.reference
            )
        )

        tx = tx_result.scalar_one_or_none()

        if not tx:
            raise HTTPException(
                status_code=404,
                detail="Transaction record not found.",
            )

        # 12. Initiate actual bank transfer
        transfer_response = await initiate_bank_transfer(
            account_number=withdrawal.account_number,
            bank_code=withdrawal.bank_code,
            amount=float(withdrawal.amount),
            source_currency=withdrawal.currency,
            destination_currency=withdrawal.currency,
            reference=withdrawal.reference,
        )

        provider_status = (
            transfer_response.get("status")
            or transfer_response
            .get("data", {})
            .get("status")
        )

        provider_status = str(
            provider_status
        ).lower()

        if provider_status not in [
            "success",
            "completed",
            "queued",
            "pending",
        ]:
            raise Exception(
                f"Transfer rejected: {transfer_response}"
            )

        # 13. Mark as processing
        withdrawal.status = (
            TransactionStatus.PROCESSING
        )

        tx.status = (
            TransactionStatus.PROCESSING
        )

        withdrawal.provider_reference = (
            transfer_response
            .get("data", {})
            .get("id")
        )

        await db.commit()

        return {
            "status": "success",
            "message": (
                "Withdrawal authorized and "
                "transfer initiated."
            ),
            "withdrawal_id": withdrawal.id,
            "reference": withdrawal.reference,
            "provider_status": provider_status,
        }

    except HTTPException:
        await db.rollback()
        raise

    except Exception as e:
        await db.rollback()

        logger.exception(
            f"Withdrawal authorization error for user {user_id}"
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to authorize withdrawal.",
        )



@router.post("/transfer")
async def transfer_funds(
    account_number: str,
    bank_code: str,
    currency: str,
    amount: float,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Capture primitive values before any commit/rollback
    user_id = str(user.id)

    reference = f"WTH-{uuid4()}"
    withdrawal_id = str(uuid4())

    amount_dec = Decimal(str(amount))

    try:
        result = await db.execute(
            select(Wallet).where(
                Wallet.user_id == user_id,
                Wallet.currency == currency,
            )
        )

        wallet = result.scalar_one_or_none()

        if not wallet:
            raise HTTPException(
                status_code=404,
                detail="Wallet not found",
            )

        if amount_dec <= 0:
            raise HTTPException(
                status_code=400,
                detail="Amount must be greater than zero",
            )

        current_balance = wallet.balance or Decimal("0")
        current_locked = wallet.locked_balance or Decimal("0")

        available_balance = (
            current_balance - current_locked
        )

        if available_balance < amount_dec:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Insufficient balance. "
                    f"Available: {available_balance} {currency}"
                ),
            )

        # Lock funds
        await Wallet.lock_balance(
            db=db,
            wallet_id=wallet.id,
            amount=amount_dec,
        )

        # Generate one-time challenge
        challenge = token_urlsafe(32)

        challenge_expires_at = (
            datetime.utcnow() + timedelta(minutes=2)
        )

        # Create withdrawal intent
        intent = WithdrawalIntent(
            id=withdrawal_id,
            user_id=user_id,
            wallet_id=wallet.id,
            reference=reference,
            amount=amount_dec,
            currency=currency,
            account_number=account_number,
            bank_code=bank_code,
            status=TransactionStatus.PENDING,
            challenge=challenge,
            challenge_expires_at=challenge_expires_at,
        )

        db.add(intent)

        # Create transaction
        tx = Transaction(
            id=str(uuid4()),
            header=TransactionHeader.WALLET_WITHDRAW.value,
            description="Wallet withdrawal",
            from_user_id=user_id,
            to_user_id=user_id,
            type=TransactionType.WITHDRAWAL,
            status=TransactionStatus.PENDING,
            from_currency=currency,
            to_currency=currency,
            from_amount=amount_dec,
            to_amount=amount_dec,
            reference=reference,
        )

        db.add(tx)

        # Make sure INSERTs happen before commit
        await db.flush()

        await db.commit()

        # Do NOT access intent.id after commit
        # Use the local primitive variables instead
        return {
            "status": "pending_verification",
            "withdrawal_id": withdrawal_id,
            "reference": reference,
            "challenge": challenge,
            "expires_in": 120,
            "amount": float(amount_dec),
            "currency": currency,
        }

    except HTTPException:
        await db.rollback()
        raise

    except Exception as e:
        await db.rollback()

        print("WITHDRAWAL ERROR:", str(e))

        logger.exception(
            f"Withdrawal creation error for user {user_id}"
        )

        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        )



@router.post("/card_pin")
async def authorize_charge(
    payload: CardPinRequest,
    user: User = Depends(get_current_user),
):
    # pmd_r8tWvRcD9u
    try:
        response = await authorize_charge_pin(
            charge_id=payload.charge_id,
            pin=payload.pin,
        )

        return {
            "success": True,
            "message": "PIN submitted successfully",
            "data": response,
        }

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


        

async def process_deposit(
    db: AsyncSession,
    data: dict,
):
    reference = data.get("reference")
    amount = Decimal(str(data.get("amount", 0)))
    currency = data.get("currency")
    status = (data.get("status") or "").upper()

    result = await db.execute(
        select(DepositIntent)
        .where(DepositIntent.reference == reference)
    )

    intent = result.scalar_one_or_none()

    if not intent:
        return {"message": "intent not found"}

    if intent.status == TransactionStatus.COMPLETED:
        return {"message": "already processed"}

    # --------------------------------------------------
    # SUCCESSFUL
    # --------------------------------------------------

    if status == "SUCCESSFUL":

        try:
            intent.status = TransactionStatus.COMPLETED
            intent.flutterwave_response = data

            tx_id = str(uuid4())

            tx = Transaction(
                id=tx_id,
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

            # Make transaction available before LedgerEntry
            await db.flush()

            await Wallet.credit_wallet(
                db=db,
                wallet_id=intent.wallet_id,
                amount=amount,
                tx_id=tx_id,
                entry_type=LedgerEntryType.DEPOSIT
            )

            # Commit transaction + wallet + ledger entry
            await db.commit()

        except Exception:
            await db.rollback()
            raise

        # Only notify after successful commit
        await manager.send_to_user(
            intent.user_id,
            {
                "type": "deposit",
                "status": "completed",
                "reference": intent.reference,
                "amount": float(intent.amount),
                "currency": intent.currency,
            },
        )

        return {
            "status": "success",
            "message": "wallet credited"
        }

    # --------------------------------------------------
    # FAILED / REVERSED / CANCELLED
    # --------------------------------------------------

    elif status in (
        "FAILED",
        "REVERSED",
        "CANCELLED",
    ):

        intent.status = TransactionStatus.FAILED
        intent.flutterwave_response = data

        await db.commit()

        await manager.send_to_user(
            intent.user_id,
            {
                "type": "deposit",
                "status": "failed",
                "reference": intent.reference,
                "amount": float(intent.amount),
                "currency": intent.currency,
            },
        )

        return {
            "status": "failed",
            "message": "transaction failed"
        }

    # --------------------------------------------------
    # UNKNOWN STATUS
    # --------------------------------------------------

    return {
        "status": "ignored",
        "message": f"Unhandled transaction status: {status}"
    }




async def process_withdrawal(
    db,
    data: dict,
):

    reference = data.get("reference")
    status = (data.get("status") or "").upper()

    async with db.begin():

        result = await db.execute(
            select(WithdrawalIntent).where(
                WithdrawalIntent.reference == reference
            )
        )


        withdrawal = result.scalar_one_or_none()
        if not withdrawal:
            return {
                "message": "Withdrawal not found"
            }


        if withdrawal.status in (
            TransactionStatus.COMPLETED,
            TransactionStatus.FAILED,
        ):
            return {"message": "Already processed"}
        
      
        wallet_result = await db.execute(
            select(Wallet)
            .where(
                Wallet.id == withdrawal.wallet_id
            )
            .with_for_update()
        )

        wallet = wallet_result.scalar_one()

        tx_result = await db.execute(
            select(Transaction)
            .where(
                Transaction.reference == reference
            )
        )

        tx = tx_result.scalar_one()

        amount = Decimal(str(withdrawal.amount))

        if status == "SUCCESSFUL":
            await Wallet.debit_wallet(
                db=db,
                wallet_id=wallet.id,
                amount=amount,
                tx_id=tx.id,
                entry_type=LedgerEntryType.WITHDRAWAL
            )
            # Finalize withdrawal
            # wallet.balance -= amount
            # wallet.locked_balance -= amount

            withdrawal.status = TransactionStatus.COMPLETED
            tx.status = TransactionStatus.COMPLETED

            await manager.send_to_user(
                withdrawal.user_id,
                {
                    "event": "withdrawal.completed",
                    "reference": withdrawal.reference,
                    "status": "COMPLETED",
                    "amount": float(amount),
                    "currency": withdrawal.currency,
                },
            )

        elif status in (
            "FAILED",
            "REVERSED",
            "CANCELLED",
        ):

           
            wallet.locked_balance -= amount

            withdrawal.status = TransactionStatus.FAILED
            tx.status = TransactionStatus.FAILED

            await manager.send_to_user(
                withdrawal.user_id,
                {
                    "event": "withdrawal.failed",
                    "reference": withdrawal.reference,
                    "status": "FAILED",
                    "amount": float(amount),
                    "currency": withdrawal.currency,
                },
            )

        else:

            return {
                "message": f"Ignoring webhook status: {status}"
            }

        return {
            "message": "Withdrawal processed"
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

        
        if event_type == "charge.completed":
            return await process_deposit(
                db,
                data
            )

        
        elif event_type == "transfer.disburse":
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