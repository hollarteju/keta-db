"""added token

Revision ID: d97be691f0ec
Revises: 1bca00e1130b
Create Date: 2025-06-18 10:23:57.113631

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd97be691f0ec'
down_revision: Union[str, None] = '1bca00e1130b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
