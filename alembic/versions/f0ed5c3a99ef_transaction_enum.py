from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'f0ed5c3a99ef'
down_revision = '88b47a91c808'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Manually alter the enum column to include new values
    op.alter_column(
        'transactions',
        'header',
        type_=mysql.ENUM(
            'Crypto Purchase Completed',
            'Crypto Sale Completed',
            'WALLET_FUND',   # newly added value
            'WALLET_WITHDRAW'  # add any other values you added
        ),
        existing_type=mysql.ENUM(
            'Crypto Purchase Completed',
            'Crypto Sale Completed'
        ),
        nullable=False
    )


def downgrade() -> None:
    # Revert the enum to the previous version
    op.alter_column(
        'transactions',
        'header',
        type_=mysql.ENUM(
            'Crypto Purchase Completed',
            'Crypto Sale Completed'
        ),
        existing_type=mysql.ENUM(
            'Crypto Purchase Completed',
            'Crypto Sale Completed',
            'WALLET_FUND',
            'WALLET_WITHDRAW'
        ),
        nullable=False
    )
