import uuid
from sqlalchemy import Column, Integer, Numeric, text, String, ForeignKey, DateTime, Boolean, Date, Time, Text, Enum, JSON, UniqueConstraint
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
    LOCKED = "locked"


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


class SwapStatus(PyEnum):
    OPEN = "open"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"


class Swap_bidstatus(PyEnum):
    ACTIVE = "active"
    EXECUTED = "executed"
    CANCELLED = "cancelled"

class DepositMethod(PyEnum):
    BANK_TRANSFER = "bank_transfer"
    CARD = "card"
    MOBILE_MONEY = "mobile_money"
    USSD = "ussd"


class NotificationType(PyEnum):
    TRANSACTION = "transaction"
    PAYMENT = "payment"
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    SWAP = "swap"
    KYC = "kyc"
    SECURITY = "security"
    ACCOUNT = "account"
    SYSTEM = "system"
    PROMOTION = "promotion"


class NotificationPriority(PyEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationStatus(PyEnum):
    UNREAD = "unread"
    READ = "read"
    ARCHIVED = "archived"


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(
        uuid.uuid4()), unique=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    full_name = Column(String(100), index=True, nullable=True)
    first_name = Column(String(100), index=True, nullable=True)
    last_name = Column(String(100), index=True, nullable=True)
    country_code = Column(String(20), nullable=True, index=True)
    phone_number = Column(String(20), nullable=True, index=True)
    address = Column(String(255), nullable=True, index=True)
    country = Column(String(100), nullable=True, index=True)
    verified_email = Column(Boolean, nullable=True, default=False, index=True)
    subscription = Column(String(50), nullable=True, index=True)
    profile_pic = Column(String(225), nullable=True, index=True)
    active = Column(Boolean, nullable=True,
                    default=False)  # Changed to Boolean
    token = Column(String(225), unique=True, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime(timezone=True),
                        default=func.now(), index=True)
    # wallet_balance = Column(Numeric(12, 2), default=text("0").00, nullable=False)
    wallets = relationship("Wallet", back_populates="user")
    sent_transactions = relationship(
        "Transaction", foreign_keys="Transaction.from_user_id", back_populates="from_user")
    received_transactions = relationship(
        "Transaction", foreign_keys="Transaction.to_user_id", back_populates="to_user")
    recipients = relationship("UserRecipient", back_populates="user")
    notifications = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="Notification.created_at.desc()"
    )
    swap_bids = relationship("SwapBid", back_populates="buyer")

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

    id = Column(String(36), primary_key=True,
                default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    currency = Column(String(10), nullable=True)  # BTC, ETH, USD, NGN
    wallet_type = Column(Enum(WalletType), nullable=False)
    balance = Column(Numeric(18, 8), default=text("0"))
    locked_balance = Column(Numeric(18, 8), default=text(
        "0"), server_default=text("0"))

    created_at = Column(DateTime(timezone=True), default=func.now())
    status = Column(Enum(WalletStatus), default=WalletStatus.ACTIVE)

    ledger_entries = relationship("LedgerEntry", back_populates="wallet")
    user = relationship("User", back_populates="wallets")
    swap_bids = relationship("SwapBid", back_populates="buyer_wallet")
    __table_args__ = (
        UniqueConstraint("user_id", "currency",
                         name="uq_user_currency_wallet"),
    )

    @staticmethod
    async def credit_wallet(db: AsyncSession, wallet_id: str, amount: Decimal, tx_id: str, entry_type: LedgerEntryType):
        if amount <= 0:
            raise ValueError("Amount must be positive")

        
        
        # Update wallet balance (materialized)
        result = await db.execute(select(Wallet).where(Wallet.id == wallet_id).with_for_update())
        wallet = result.scalar_one()
        wallet.balance = (wallet.balance or 0) + amount
        db.add(wallet)

        # Create ledger entry
        entry = LedgerEntry(
            wallet_id=wallet_id,
            amount=amount,
            transaction_id=tx_id,
            entry_type=entry_type
        )
        db.add(entry)

        return wallet.balance

    @staticmethod
    async def debit_wallet(db: AsyncSession, wallet_id: str, amount: Decimal, tx_id: str, entry_type: LedgerEntryType):
        if amount <= 0:
            raise ValueError("Amount must be positive")

        result = await db.execute(select(Wallet).where(Wallet.id == wallet_id).with_for_update())
        wallet = result.scalar_one()

        if wallet.balance < amount:
            raise InsufficientFundsError("Insufficient wallet balance")

        
        wallet.balance -= amount
        db.add(wallet)
        
        entry = LedgerEntry(
                    wallet_id=wallet_id,
                    amount=-amount,
                    transaction_id=tx_id,
                    entry_type=entry_type
                )
        db.add(entry)
        # await db.commit()
        # await db.refresh(wallet)
        return wallet.balance

    @classmethod
    async def get_wallet_balance(cls, db: AsyncSession, wallet_id: str) -> int:
        result = await db.execute(
            select(func.coalesce(func.sum(LedgerEntry.amount), 0))
            .where(LedgerEntry.wallet_id == wallet_id)
        )
        return result.scalar_one()

    @staticmethod
    async def lock_balance(db: AsyncSession, wallet_id: str, amount: Decimal):
        result = await db.execute(
            select(Wallet).where(Wallet.id == wallet_id).with_for_update()
        )
        wallet = result.scalar_one()
        # print(f"check wallet: {wallet.locked_balance}")
        available_balance = wallet.balance
        if wallet.locked_balance:
            available_balance = wallet.balance - wallet.locked_balance

        if available_balance < amount:
            raise InsufficientFundsError("Insufficient available balance")

        wallet.locked_balance += amount
        print(f"check wallet: {wallet.locked_balance}")
        db.add(wallet)

        return wallet

    @staticmethod
    async def unlock_balance(db: AsyncSession, wallet_id: str, amount: Decimal):
        """In case withdrawal fails"""
        result = await db.execute(
            select(Wallet).where(Wallet.id == wallet_id).with_for_update()
        )
        wallet = result.scalar_one()
        wallet.locked_balance = (
            wallet.locked_balance or Decimal("0")) - amount
        return wallet

    @staticmethod
    async def spend_locked_balance(db: AsyncSession, wallet_id: str, amount: Decimal):
        result = await db.execute(
            select(Wallet).where(Wallet.id == wallet_id).with_for_update()
        )
        wallet = result.scalar_one()

        if wallet.locked_balance < amount:
            raise InsufficientFundsError("Insufficient locked balance")

        wallet.locked_balance -= amount

        db.add(wallet)
        # await db.commit()
        # await db.refresh(wallet)

        return wallet


class DepositIntent(Base):
    __tablename__ = "deposit_intents"

    id = Column(String(36), primary_key=True,
                default=lambda: str(uuid.uuid4()))

    user_id = Column(String(36), ForeignKey(
        "users.id"), nullable=False, index=True)
    wallet_id = Column(String(36), ForeignKey(
        "wallets.id"), nullable=False, index=True)

    reference = Column(String(100), unique=True, index=True, nullable=False)

    amount = Column(Numeric(18, 2), nullable=False)
    currency = Column(String(10), nullable=False)

    method = Column(Enum(DepositMethod), nullable=False)

    status = Column(
        Enum(TransactionStatus),
        default=TransactionStatus.PENDING,
        index=True
    )
    flutterwave_response = Column(JSON, nullable=True)

    expires_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        default=func.now(), onupdate=func.now())

    # relationships
    user = relationship("User")
    wallet = relationship("Wallet")


class UserRecipient(Base):
    __tablename__ = "user_recipients"

    id = Column(String(36), primary_key=True,
                default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    recipient_id = Column(String(255), nullable=False)
    account_number = Column(String(20), nullable=False)
    bank_code = Column(String(10), nullable=False)
    bank_name = Column(String(100), nullable=True)
    is_default = Column(Boolean, default=False)  # ⭐ important
    created_at = Column(DateTime, default=func.now())
    user = relationship("User", back_populates="recipients")

    __table_args__ = (
        UniqueConstraint("user_id", "account_number",
                         "bank_code", name="uq_user_bank"),
    )


class InsufficientFundsError(Exception):
    pass


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id = Column(String(36), primary_key=True,
                default=lambda: str(uuid.uuid4()))
    wallet_id = Column(String(36), ForeignKey(
        "wallets.id"), nullable=False, index=True)
    transaction_id = Column(String(36), ForeignKey(
        "transactions.id"), nullable=False, index=True)

    amount = Column(Numeric(18, 8), nullable=False)
    entry_type = Column(Enum(LedgerEntryType), nullable=False)

    created_at = Column(DateTime(timezone=True), default=func.now())

    __table_args__ = (
        UniqueConstraint("wallet_id", "transaction_id", name="uq_wallet_tx"),
    )

    wallet = relationship("Wallet", back_populates="ledger_entries")
    transaction = relationship("Transaction")


class Asset(Base):
    __tablename__ = "assets"

    id = Column(String(36), primary_key=True,
                default=lambda: str(uuid.uuid4()))
    name = Column(String(50), nullable=False)   # Bitcoin
    symbol = Column(String(10), nullable=False)  # BTC
    is_crypto = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), default=func.now())


class ExchangeRate(Base):
    __tablename__ = "exchange_rates"

    id = Column(String(36), primary_key=True,
                default=lambda: str(uuid.uuid4()))
    from_currency = Column(String(10), nullable=False)
    to_currency = Column(String(10), nullable=False)

    rate = Column(Integer, nullable=False)  # multiplied rate for precision
    updated_at = Column(DateTime(timezone=True), default=func.now())
    __table_args__ = (
        UniqueConstraint("from_currency", "to_currency",
                         name="uq_currency_pair"),
    )


class GiftCard(Base):
    __tablename__ = "gift_cards"

    id = Column(String(36), primary_key=True,
                default=lambda: str(uuid.uuid4()))
    brand = Column(String(100), nullable=False)
    country = Column(String(50))
    value = Column(Integer, nullable=False)
    currency = Column(String(10), nullable=False)

    created_at = Column(DateTime(timezone=True), default=func.now())


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String(36), primary_key=True,
                default=lambda: str(uuid.uuid4()))

    header = Column(String(50), nullable=False)
    description = Column(String(200), nullable=False)
    from_user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    to_user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    type = Column(Enum(TransactionType), nullable=False)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.PENDING)

    from_currency = Column(String(10))
    to_currency = Column(String(10))

    from_amount = Column(Numeric(18, 2), nullable=False)
    to_amount = Column(Numeric(18, 2), nullable=True)

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

    id = Column(String(36), primary_key=True,
                default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"))
    wallet_id = Column(String(36), ForeignKey("wallets.id"), nullable=False)
    transaction_id = Column(String(36), ForeignKey(
        "transactions.id"), nullable=False)
    fee = Column(Integer, default=text("0"))

    currency = Column(String(10))
    amount = Column(Integer)
    destination = Column(String(255))

    status = Column(Enum(TransactionStatus))
    created_at = Column(DateTime(timezone=True), default=func.now())


class WithdrawalIntent(Base):
    __tablename__ = "withdrawal_intents"

    id = Column(String(36), primary_key=True,
                default=lambda: str(uuid.uuid4()))

    user_id = Column(String(36), ForeignKey("users.id"), index=True)
    wallet_id = Column(String(36), ForeignKey("wallets.id"), index=True)

    reference = Column(String(100), unique=True, index=True)

    amount = Column(Numeric(18, 2), nullable=False)
    currency = Column(String(10), nullable=False)

    account_number = Column(String(30), nullable=False)
    bank_code = Column(String(20), nullable=False)

    status = Column(Enum(TransactionStatus), default=TransactionStatus.PENDING)

    flutterwave_response = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), default=func.now())


class Swap(Base):
    __tablename__ = "swaps"

    id = Column(String(36), primary_key=True,
                default=lambda: str(uuid.uuid4()))
    wallet_id = Column(String(36), ForeignKey("wallets.id"), nullable=False)
    creator_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    from_currency = Column(String(10), nullable=False)
    to_currency = Column(String(10), nullable=False)

    amount = Column(Integer, nullable=False)
    min_amount = Column(Integer, nullable=False)
    remaining_amount = Column(Integer, nullable=False)

    rate = Column(Integer, nullable=False)
    min_rate = Column(Integer, nullable=True)
    expires_at = Column(DateTime(timezone=True))
    status = Column(Enum(SwapStatus), default=SwapStatus.OPEN)

    created_at = Column(DateTime(timezone=True), default=func.now())

    creator = relationship("User")
    swap_bids = relationship("SwapBid", back_populates="swap")

    def validate_order_amount(self, amount: int):

        if self.min_amount and amount < self.min_amount:
            return False

        # check remaining liquidity
        if amount > self.remaining_amount:
            return False

        # check invalid amounts
        if amount <= 0:
            return False

        return True
    



class SwapBid(Base):
    __tablename__ = "swap_bids"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    swap_id = Column(
        String(36),
        ForeignKey("swaps.id"),
        nullable=False,
        index=True
    )

    buyer_id = Column(
        String(36),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    buyer_wallet_id = Column(
        String(36),
        ForeignKey("wallets.id"),
        nullable=False,
        index=True
    )

    amount = Column(
            Numeric(18, 8),
            nullable=False
        )

    # Buyer's proposed rate
    bid_rate = Column(
        Numeric(18, 8),
        nullable=False
    )

    # Amount locked in buyer's payment wallet
    locked_amount = Column(
        Numeric(18, 8),
        nullable=False
    )

    status = Column(
        Enum(Swap_bidstatus),
        nullable=False,
        default=Swap_bidstatus.ACTIVE,
        index=True
    )

    created_at = Column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False
    )

    updated_at = Column(
        DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    swap = relationship("Swap")
    buyer = relationship("User")
    buyer_wallet = relationship("Wallet")

     

class SwapExecution(Base):
    __tablename__ = "swap_executions"

    id = Column(String(36), primary_key=True,
                default=lambda: str(uuid.uuid4()))

    swap_id = Column(String(36), ForeignKey("swaps.id"), nullable=False)

    taker_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    amount = Column(Integer, nullable=False)
    rate = Column(Integer, nullable=False)
    from_currency = Column(String(10))
    to_currency = Column(String(10))
    fee = Column(Numeric(18, 8), default=text("0"))
    transaction_id = Column(String(36), ForeignKey("transactions.id"))

    created_at = Column(DateTime(timezone=True), default=func.now())

    swap = relationship("Swap")
    taker = relationship("User")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    user_id = Column(
        String(36),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    type = Column(
        Enum(NotificationType),
        nullable=False,
        index=True
    )

    priority = Column(
        Enum(NotificationPriority),
        nullable=False,
        default=NotificationPriority.NORMAL,
        index=True
    )

    status = Column(
        Enum(NotificationStatus),
        nullable=False,
        default=NotificationStatus.UNREAD,
        index=True
    )

    title = Column(
        String(150),
        nullable=False
    )

    message = Column(
        Text,
        nullable=False
    )

    short_message = Column(
        String(255),
        nullable=True
    )

    action_url = Column(
        String(500),
        nullable=True
    )

    action_label = Column(
        String(100),
        nullable=True
    )


    reference_id = Column(
        String(36),
        nullable=True,
        index=True
    )

    reference_type = Column(
        String(50),
        nullable=True,
        index=True
    )

    extra_data = Column(
        JSON,
        nullable=True
    )

  
    push_enabled = Column(
        Boolean,
        default=True,
        nullable=False
    )

    email_enabled = Column(
        Boolean,
        default=False,
        nullable=False
    )

   
    push_sent = Column(
        Boolean,
        default=False,
        nullable=False
    )

    email_sent = Column(
        Boolean,
        default=False,
        nullable=False
    )

    
    read_at = Column(
        DateTime(timezone=True),
        nullable=True
    )

    archived_at = Column(
        DateTime(timezone=True),
        nullable=True
    )

    expires_at = Column(
        DateTime(timezone=True),
        nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False,
        index=True
    )

    updated_at = Column(
        DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    user = relationship(
        "User",
        back_populates="notifications"
    )

    def mark_as_read(self):
        self.status = NotificationStatus.READ
        self.read_at = datetime.utcnow()

    def archive(self):
        self.status = NotificationStatus.ARCHIVED
        self.archived_at = datetime.utcnow()

    @property
    def is_read(self):
        return self.status == NotificationStatus.READ
