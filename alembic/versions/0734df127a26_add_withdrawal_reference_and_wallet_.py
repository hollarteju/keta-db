"""add withdrawal reference and wallet fixes

Revision ID: 0734df127a26
Revises: 9afd5677715a
Create Date: 2026-05-22 15:49:34.528727

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0734df127a26'
down_revision: Union[str, None] = '9afd5677715a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
