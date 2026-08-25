"""notification model created

Revision ID: 7e446f588194
Revises: 0a9a5e2efb60
Create Date: 2026-08-13 12:34:59.396327

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7e446f588194'
down_revision: Union[str, None] = '0a9a5e2efb60'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
