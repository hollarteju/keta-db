"""create user settings

Revision ID: 81289a9455e3
Revises: 94df88322942
Create Date: 2026-09-25 20:21:17.142712

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "81289a9455e3"
down_revision: Union[str, None] = "94df88322942"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "settings",

        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "user_id",
            sa.String(length=36),
            nullable=False,
        ),

        sa.Column(
            "two_factor_enabled",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),

        sa.Column(
            "two_factor_methods",
            sa.JSON(),
            nullable=True,
        ),

        sa.Column(
            "login_notifications",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),

        sa.Column(
            "biometric_enabled",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),

        sa.Column(
            "daily_transaction_limit",
            sa.Numeric(precision=18, scale=2),
            nullable=True,
        ),

        sa.Column(
            "payment_confirmation",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),

        sa.Column(
            "p2p_enabled",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),

        sa.Column(
            "p2p_trade_notifications",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),

        sa.Column(
            "profile_visible",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),

        sa.Column(
            "analytics_enabled",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),

        sa.Column(
            "push_notifications",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),

        sa.Column(
            "email_notifications",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),

        sa.Column(
            "sms_notifications",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),

        sa.PrimaryKeyConstraint("id"),

        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),

        sa.UniqueConstraint("user_id"),
    )

    op.create_index(
        op.f("ix_settings_id"),
        "settings",
        ["id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_settings_id"),
        table_name="settings",
    )

    op.drop_table("settings")