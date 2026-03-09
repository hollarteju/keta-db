"""add min_amount to swapss

Revision ID: fd65f33299e2
Revises: e965ba1fa02e
Create Date: 2026-03-09 15:41:35.906976

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fd65f33299e2'
down_revision: Union[str, None] = 'e965ba1fa02e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
