"""withdrawalintend  signature created

Revision ID: fa768ed66c5a
Revises: 2e0bceb19713
Create Date: 2026-10-02 17:39:19.557904

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fa768ed66c5a'
down_revision: Union[str, None] = '2e0bceb19713'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
