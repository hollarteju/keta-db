"""Add from_user_id and to_user_id to transactions

Revision ID: 8daaf5df0316
Revises: 0fb09a636d1f
Create Date: 2026-01-20 16:12:44.733839

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8daaf5df0316'
down_revision: Union[str, None] = '0fb09a636d1f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
