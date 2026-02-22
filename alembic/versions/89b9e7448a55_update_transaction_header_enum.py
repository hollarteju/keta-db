"""update transaction header enum

Revision ID: 89b9e7448a55
Revises: f0ed5c3a99ef
Create Date: 2026-02-14 13:56:28.570228

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '89b9e7448a55'
down_revision: Union[str, None] = 'f0ed5c3a99ef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
