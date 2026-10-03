"""fix_transaction_device_id_type

Revision ID: 6aa35b5948e2
Revises: 7500cd99e64d
Create Date: 2026-10-02 18:31:24.484778

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6aa35b5948e2'
down_revision: Union[str, None] = '7500cd99e64d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
