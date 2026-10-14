"""Add standalone orders.created_at index for unfiltered admin list sort

Revision ID: a5b6c7d8e9f0
Revises: f4a5b6c7d8e9
Create Date: 2026-10-15 00:01:00.000000

The composite indexes (user_id, created_at) and (status, created_at) cover
filtered order lists, but admin_list_orders with no status filter runs a
global ORDER BY created_at DESC — this index lets Postgres satisfy the sort
directly instead of an in-memory sort.
"""
from typing import Sequence, Union

from alembic import op

revision: str = 'a5b6c7d8e9f0'
down_revision: Union[str, Sequence[str], None] = 'f4a5b6c7d8e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index('ix_orders_created_at', 'orders', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_orders_created_at', table_name='orders')
