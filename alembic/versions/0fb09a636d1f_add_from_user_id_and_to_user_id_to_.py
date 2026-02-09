"""Add from_user_id and to_user_id to transactions

Revision ID: 0fb09a636d1f
Revises: 4cc6a9e1b787
Create Date: 2026-01-20 15:46:41.335403

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0fb09a636d1f'
down_revision: Union[str, None] = '4cc6a9e1b787'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
