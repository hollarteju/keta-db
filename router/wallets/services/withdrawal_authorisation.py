from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction_device import TransactionDevice
from app.models.withdrawal_authorization_challenge import (
    WithdrawalAuthorizationChallenge,
)
from app.utils.withdrawal_challenge import (
    build_withdrawal_challenge,
    generate_nonce,
)


class WithdrawalAuthorizationService:

    CHALLENGE_EXPIRY_MINUTES = 2

    @staticmethod
    async def get_active_device(
        db: AsyncSession,
        user_id: str,
    ) -> TransactionDevice:

        result = await db.execute(
            select(TransactionDevice).where(
                TransactionDevice.user_id == user_id,
                TransactionDevice.status == "ACTIVE",
            )
        )

        device = result.scalar_one_or_none()

        if not device:
            raise HTTPException(
                status_code=400,
                detail=(
                    "No active transaction device. "
                    "Please register this device first."
                ),
            )

        return device

    @staticmethod
    async def create_challenge(
        *,
        db: AsyncSession,
        user_id: str,
        withdrawal,
    ):

        device = await WithdrawalAuthorizationService.get_active_device(
            db,
            user_id,
        )

        # Prevent multiple active challenges for same withdrawal.
        result = await db.execute(
            select(
                WithdrawalAuthorizationChallenge
            ).where(
                WithdrawalAuthorizationChallenge.withdrawal_id
                == str(withdrawal.id),
                WithdrawalAuthorizationChallenge.user_id
                == user_id,
                WithdrawalAuthorizationChallenge.used_at
                .is_(None),
            )
        )

        existing = result.scalar_one_or_none()

        if existing and existing.expires_at > datetime.utcnow():
            return existing

        nonce = generate_nonce()

        expires_at = (
            datetime.utcnow()
            + timedelta(
                minutes=WithdrawalAuthorizationService
                .CHALLENGE_EXPIRY_MINUTES
            )
        )

        # Create temporary challenge first so we have an ID.
        challenge = WithdrawalAuthorizationChallenge(
            user_id=user_id,
            withdrawal_id=str(withdrawal.id),
            device_id=device.id,
            nonce=nonce,
            challenge_message="PENDING",
            expires_at=expires_at,
        )

        db.add(challenge)

        await db.flush()

        message = build_withdrawal_challenge(
            challenge_id=challenge.id,
            withdrawal_id=str(withdrawal.id),
            user_id=user_id,
            amount=withdrawal.amount,
            currency=withdrawal.currency,
            network=withdrawal.network,
            destination=withdrawal.destination,
            nonce=nonce,
        )

        challenge.challenge_message = message

        await db.commit()
        await db.refresh(challenge)

        return challenge