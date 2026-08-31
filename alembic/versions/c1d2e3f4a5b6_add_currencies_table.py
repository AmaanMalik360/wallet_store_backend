"""Add currencies table

Revision ID: c1d2e3f4a5b6
Revises: e16bc5fb6fb2
Create Date: 2026-06-01 00:00:00.000000

NOTE (future): Add new ISO 4217 codes here (e.g. USD, EUR) when expanding to
multi-currency. Update CurrencySeeder accordingly. Do NOT seed inside migrations
to avoid re-seeding on rollback/replay.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, Sequence[str], None] = '0971be3e9ab9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'currencies',
        sa.Column('code', sa.CHAR(3), primary_key=True),
        sa.Column('decimal_places', sa.SmallInteger(), nullable=False, server_default='2'),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
    )
    
    # Insert PKR row so migration #3 can add FK constraint.
    # NOTE: CurrencySeeder can be run after all migrations to ensure this row exists.
    op.execute(
        "INSERT INTO currencies (code, decimal_places, is_default) "
        "VALUES ('PKR', 2, true)"
    )


def downgrade() -> None:
    op.drop_table('currencies')
