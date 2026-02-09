"""Add from_user_id and to_user_id to transactions

Revision ID: 4cc6a9e1b787
Revises: 6906b563e507
Create Date: 2026-01-20 15:32:51.569709

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4cc6a9e1b787'
down_revision: Union[str, None] = '6906b563e507'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
