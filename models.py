import uuid
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Date, Time, Text, Enum, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base
from sqlalchemy.sql import select, func

from passlib.context import CryptContext
from datetime import datetime, date, time, timedelta
from enum import Enum as PyEnum
from sqlalchemy.ext.asyncio import AsyncSession





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


class TransactionStatus(PyEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WalletType(PyEnum):
    FIAT = "fiat"
    CRYPTO = "crypto"


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

    wallets = relationship("Wallet", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")

    
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

    currency = Column(String(10), nullable=False)  # BTC, ETH, USD, NGN
    wallet_type = Column(Enum(WalletType), nullable=False)

    created_at = Column(DateTime(timezone=True), default=func.now())
    status = Column(Enum(WalletStatus), default=WalletStatus.ACTIVE)
    
    ledger_entries = relationship("LedgerEntry", back_populates="wallet")
    user = relationship("User", back_populates="wallets")
    __table_args__ = (
    UniqueConstraint("user_id", "currency", name="uq_user_currency_wallet"),
)


    @staticmethod
    async def get_wallet_balance(db: AsyncSession, wallet_id: str) -> int:
        result = await db.execute(
            select(func.coalesce(func.sum(LedgerEntry.amount), 0))
            .where(LedgerEntry.wallet_id == wallet_id)
        )
        return result.scalar_one()

    @staticmethod
    async def debit_wallet(db: AsyncSession, wallet_id: str, amount: int, tx_id: str):
        if amount <= 0:
            raise ValueError("Invalid amount")

        async with db.begin():
            await db.execute(
                select(Wallet)
                .where(Wallet.id == wallet_id)
                .with_for_update()
            )

            if Wallet.status != WalletStatus.ACTIVE:
                raise Exception("Wallet is frozen")

            balance = await Wallet.get_wallet_balance(db, wallet_id)

            if balance < amount:
                raise InsufficientFundsError()

            entry = LedgerEntry(
                wallet_id=wallet_id,
                amount=-amount,
                transaction_id=tx_id,
                entry_type=LedgerEntryType.WITHDRAWAL  # or BUY, FEE, etc
            )


            db.add(entry)

    @staticmethod
    async def credit_wallet(db: AsyncSession, wallet_id: str, amount: int, tx_id: str):
        if amount <= 0:
            raise ValueError("Invalid amount")

        async with db.begin():
            await db.execute(
                select(Wallet)
                .where(Wallet.id == wallet_id)
                .with_for_update()
            )

            entry = LedgerEntry(
                wallet_id=wallet_id,
                amount=-amount,
                transaction_id=tx_id,
                entry_type=LedgerEntryType.DEPOSIT  # or BUY, FEE, etc
            )


            db.add(entry)


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
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    type = Column(Enum(TransactionType), nullable=False)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.PENDING)

    from_currency = Column(String(10))
    to_currency = Column(String(10))

    from_amount = Column(Integer, nullable=False)
    to_amount = Column(Integer, nullable=True)

    rate = Column(Integer)
    reference = Column(String(100), unique=True, index=True)


    created_at = Column(DateTime(timezone=True), default=func.now())
    

    user = relationship("User", back_populates="transactions")
    


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
    
