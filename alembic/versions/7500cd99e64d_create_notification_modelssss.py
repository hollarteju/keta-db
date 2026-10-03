"""create notification modelssss

Revision ID: 7500cd99e64d
Revises: fa768ed66c5a
Create Date: 2026-10-02 17:59:02.030386

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7500cd99e64d'
down_revision: Union[str, None] = 'fa768ed66c5a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Columns challenge, challenge_expires_at, challenge_used_at 
    # and transaction_device_id already exist in the database.
    # We only need to fix the type of transaction_device_id
    # and then create the foreign key.

    # 1. Change the column type from VARCHAR(36) → INTEGER
    op.alter_column(
        'withdrawal_intents',
        'transaction_device_id',
        existing_type=sa.String(length=36),
        type_=sa.Integer(),
        existing_nullable=True,
    )

    # 2. Create the foreign key
    op.create_foreign_key(
        'fk_withdrawal_intents_transaction_device',
        'withdrawal_intents',
        'transaction_devices',
        ['transaction_device_id'],
        ['id'],
    )


def downgrade() -> None:
    # Drop the foreign key first
    op.drop_constraint(
        'fk_withdrawal_intents_transaction_device',
        'withdrawal_intents',
        type_='foreignkey'
    )

    # Change the column type back to VARCHAR(36)
    op.alter_column(
        'withdrawal_intents',
        'transaction_device_id',
        existing_type=sa.Integer(),
        type_=sa.String(length=36),
        existing_nullable=True,
    )