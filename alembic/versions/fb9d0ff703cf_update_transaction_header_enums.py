"""update transaction header enums

Revision ID: fb9d0ff703cf
Revises: 89b9e7448a55
Create Date: 2026-02-14 13:59:34.444801

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fb9d0ff703cf'
down_revision: Union[str, None] = '89b9e7448a55'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
