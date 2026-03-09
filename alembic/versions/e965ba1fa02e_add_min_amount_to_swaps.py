"""add min_amount to swaps

Revision ID: e965ba1fa02e
Revises: a06e9df2c85b
Create Date: 2026-03-09 15:41:01.188831

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e965ba1fa02e'
down_revision: Union[str, None] = 'a06e9df2c85b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
