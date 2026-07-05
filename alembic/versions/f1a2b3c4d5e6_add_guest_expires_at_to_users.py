"""Add guest_expires_at to users table

Revision ID: f1a2b3c4d5e6
Revises: e16bc5fb6fb2
Create Date: 2026-06-21 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = '5dd335e57947'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add guest_expires_at column for tracking guest account expiry
    op.add_column(
        "users",
        sa.Column(
            "guest_expires_at",
            sa.DateTime(timezone=True),
            nullable=True
        )
    )


def downgrade() -> None:
    op.drop_column("users", "guest_expires_at")
