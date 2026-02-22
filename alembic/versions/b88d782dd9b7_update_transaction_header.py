"""update transaction header

Revision ID: b88d782dd9b7
Revises: fb9d0ff703cf
Create Date: 2026-02-14 14:01:58.177852

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b88d782dd9b7'
down_revision: Union[str, None] = 'fb9d0ff703cf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
