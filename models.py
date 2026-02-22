import uuid
from sqlalchemy import Column, Integer, Numeric, String, ForeignKey, DateTime, Boolean, Date, Time, Text, Enum, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base
from sqlalchemy.sql import select, func

from passlib.context import CryptContext
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal

import re



pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
def str_to_uuid(value: str) -> uuid.UUID:
    """Convert string to UUID if value is not None/empty."""
    return uuid.UUID(value) if value else None

class TransactionType(PyEnum):
    BUY = "buy"
    SELL = "sell"
    EXCHANGE = "exchange"
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"


class TransactionDirection:
    CREDIT_TYPES = {
        TransactionType.DEPOSIT,
        TransactionType.SELL,
    }

    DEBIT_TYPES = {
        TransactionType.WITHDRAWAL,
        TransactionType.BUY,
    }

    NEUTRAL_TYPES = {
        TransactionType.EXCHANGE,
    }

class TransactionStatus(PyEnum):
    PENDING = "Pending"
    PROCESSING = "Processing"
    COMPLETED = "Completed"
    FAILED = "Failed"
    FUND_RELEASED = "Fund released"
    UNDER_REVIEW = "Under review"
    CANCELLED = "Cancelled"


class WalletType(PyEnum):
    FIAT = "fiat"
    CRYPTO = "crypto"

class CurrencyType(PyEnum):
    NAIRA = "NGN"
    DOLLAR = "USD"
    
class CurrencySymbol: 
    CURRENCY_SYMBOL = {
    CurrencyType.NAIRA: "₦",
    CurrencyType.DOLLAR: "$"
}

class KYCStatus(PyEnum):
    NOT_SUBMITTED = "not_submitted"
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"

class LedgerEntryType(PyEnum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    BUY = "buy"
    SELL = "sell"
    FEE = "fee"


class WalletStatus(PyEnum):
    ACTIVE = "active"
    FROZEN = "frozen"


class TransactionHeader(PyEnum):
    WALLET_FUND = "Wallet Funding"
    WALLET_WITHDRAW = "Wallet Withdrawal"
    CRYPTO_PURCHASE = "Crypto Purchase Completed"
    CRYPTO_SALE = "Crypto Sale Completed"
    PLATFORM_PAYMENT = "Service Payment"


class TransactionDetails(Enum):
    CRYPTO_PURCHASE = "You bought {amount} {crypto} for ${price} USD"


class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), unique=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    full_name = Column(String(100), index=True, nullable=True)
    phone_number = Column(String(20), nullable=True, index=True)
    address = Column(String(255), nullable=True, index=True)
    country = Column(String(100), nullable=True, index=True)
    verified_email = Column(Boolean, nullable=True, default=False, index=True)
    subscription = Column(String(50), nullable=True, index=True)
    profile_pic = Column(String(225), nullable=True, index=True)
    active = Column(Boolean, nullable=True, default=False)  # Changed to Boolean
    token = Column(String(225), unique=True, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), index=True)
    # wallet_balance = Column(Numeric(12, 2), default=0.00, nullable=False)
    wallets = relationship("Wallet", back_populates="user")
    sent_transactions = relationship("Transaction", foreign_keys="Transaction.from_user_id", back_populates="from_user")
    received_transactions = relationship("Transaction", foreign_keys="Transaction.to_user_id", back_populates="to_user")

    def is_valid_password(pw: str) -> bool:
        return bool(re.fullmatch(r"\d{6}", pw))

    def verify_password(self, plain_password: str) -> bool:
        return pwd_context.verify(plain_password, self.password)
    
    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)
        
    def validate_token(self, token: str):
        if self.token != token:
            raise ValueError("Invalid verification token")
        elif self.token_expires_at is None or self.token_expires_at < datetime.utcnow():
            raise ValueError("Verification token has expired")
    
class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    currency = Column(String(10), nullable=True)  # BTC, ETH, USD, NGN
    wallet_type = Column(Enum(WalletType), nullable=False)
    balance = Column(Numeric(12, 2), default=0.00)

    created_at = Column(DateTime(timezone=True), default=func.now())
    status = Column(Enum(WalletStatus), default=WalletStatus.ACTIVE)
    
    ledger_entries = relationship("LedgerEntry", back_populates="wallet")
    user = relationship("User", back_populates="wallets")
    __table_args__ = (
    UniqueConstraint("user_id", "currency", name="uq_user_currency_wallet"),
)


    @staticmethod
    async def credit_wallet(db: AsyncSession, wallet_id: str, amount: Decimal, tx_id: str):
        if amount <= 0:
            raise ValueError("Amount must be positive")

        # Create ledger entry
        entry = LedgerEntry(
            wallet_id=wallet_id,
            amount=amount,
            transaction_id=tx_id,
            entry_type=LedgerEntryType.DEPOSIT
        )
        db.add(entry)

        # Update wallet balance (materialized)
        result = await db.execute(select(Wallet).where(Wallet.id == wallet_id).with_for_update())
        wallet = result.scalar_one()
        wallet.balance = (wallet.balance or 0) + amount
        db.add(wallet)
        await db.commit()
        await db.refresh(wallet)
        return wallet.balance

    @staticmethod
    async def debit_wallet(db: AsyncSession, wallet_id: str, amount: Decimal, tx_id: str):
        if amount <= 0:
            raise ValueError("Amount must be positive")

        result = await db.execute(select(Wallet).where(Wallet.id == wallet_id).with_for_update())
        wallet = result.scalar_one()

        if wallet.balance < amount:
            raise InsufficientFundsError("Insufficient wallet balance")

        entry = LedgerEntry(
            wallet_id=wallet_id,
            amount=-amount,
            transaction_id=tx_id,
            entry_type=LedgerEntryType.WITHDRAWAL
        )
        db.add(entry)

        wallet.balance -= amount
        db.add(wallet)
        await db.commit()
        await db.refresh(wallet)
        return wallet.balance
    
    @classmethod
    async def get_wallet_balance(cls, db: AsyncSession, wallet_id: str) -> int:
        result = await db.execute(
            select(func.coalesce(func.sum(LedgerEntry.amount), 0))
            .where(LedgerEntry.wallet_id == wallet_id)
        )
        return result.scalar_one()

class InsufficientFundsError(Exception):
    pass


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    wallet_id = Column(String(36), ForeignKey("wallets.id"), nullable=False, index=True)
    transaction_id = Column(String(36), ForeignKey("transactions.id"), nullable=False, index=True)

    amount = Column(Integer, nullable=False)
    entry_type = Column(Enum(LedgerEntryType), nullable=False)

    created_at = Column(DateTime(timezone=True), default=func.now())

    __table_args__ = (
        UniqueConstraint("wallet_id", "transaction_id", name="uq_wallet_tx"),
    )

    wallet = relationship("Wallet", back_populates="ledger_entries")
    transaction = relationship("Transaction")

    



class Asset(Base):
    __tablename__ = "assets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(50), nullable=False)   # Bitcoin
    symbol = Column(String(10), nullable=False) # BTC
    is_crypto = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), default=func.now())

class ExchangeRate(Base):
    __tablename__ = "exchange_rates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    from_currency = Column(String(10), nullable=False)
    to_currency = Column(String(10), nullable=False)

    rate = Column(Integer, nullable=False)  # multiplied rate for precision
    updated_at = Column(DateTime(timezone=True), default=func.now())
    __table_args__ = (
    UniqueConstraint("from_currency", "to_currency", name="uq_currency_pair"),
)

class GiftCard(Base):
    __tablename__ = "gift_cards"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    brand = Column(String(100), nullable=False)
    country = Column(String(50))
    value = Column(Integer, nullable=False)
    currency = Column(String(10), nullable=False)

    created_at = Column(DateTime(timezone=True), default=func.now())


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    header = Column(String(50), nullable=False) 
    description = Column(String(200), nullable=False)
    from_user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    to_user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    type = Column(Enum(TransactionType), nullable=False)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.PENDING)

    from_currency = Column(String(10))
    to_currency = Column(String(10))

    from_amount = Column(Integer, nullable=False)
    to_amount = Column(Integer, nullable=True)

    rate = Column(Integer)
    reference = Column(String(100), unique=True, index=True)

    created_at = Column(DateTime(timezone=True), default=func.now())

    # 🔁 Relationships
    from_user = relationship("User", foreign_keys=[from_user_id])
    to_user = relationship("User", foreign_keys=[to_user_id])

    def is_credit(self) -> bool:
        return self.type in TransactionDirection.CREDIT_TYPES

    def is_debit(self) -> bool:
        return self.type in TransactionDirection.DEBIT_TYPES

    def formatted_amount(self) -> str:
        if self.is_credit():
            return f"+{self.to_amount} {self.to_currency}"

        if self.is_debit():
            return f"-{self.from_amount} {self.from_currency}"

        return f"{self.from_amount} {self.from_currency}"

    def ui_metadata(self):
        if self.is_credit():
            return {
                "icon": "arrow-up",
                "color": "#22C55E"
            }

        if self.is_debit():
            return {
                "icon": "arrow-down",
                "color": "#EF4444"
            }

        return {
            "icon": "arrow-right",
            "color": "#6B7280"
        }


class Withdrawal(Base):
    __tablename__ = "withdrawals"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"))
    wallet_id = Column(String(36), ForeignKey("wallets.id"), nullable=False)
    transaction_id = Column(String(36), ForeignKey("transactions.id"), nullable=False)
    fee = Column(Integer, default=0)


    currency = Column(String(10))
    amount = Column(Integer)
    destination = Column(String(255))

    status = Column(Enum(TransactionStatus), default=TransactionStatus.PENDING)
    created_at = Column(DateTime(timezone=True), default=func.now())
    
