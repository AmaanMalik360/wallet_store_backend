"""add_addresses_table_and_update_orders

Revision ID: 0971be3e9ab9
Revises: b1c2d3e4f5a6
Create Date: 2026-08-10 03:41:20.139239

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0971be3e9ab9'
down_revision: Union[str, Sequence[str], None] = 'b1c2d3e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'addresses',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('line1', sa.String(length=255), nullable=False),
        sa.Column('line2', sa.String(length=255), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=False),
        sa.Column('state', sa.String(length=100), nullable=True),
        sa.Column('postal_code', sa.String(length=20), nullable=True),
        sa.Column('country', sa.String(length=2), nullable=False),
        sa.Column('label', sa.String(length=50), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.add_column('orders', sa.Column('shipping_address_id', sa.UUID(), nullable=True))
    op.add_column('orders', sa.Column('billing_address_id', sa.UUID(), nullable=True))
    op.add_column('orders', sa.Column('source', sa.String(length=20), nullable=True))
    op.add_column('orders', sa.Column('notes', sa.Text(), nullable=True))
    op.create_foreign_key('fk_orders_shipping_address', 'orders', 'addresses', ['shipping_address_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_orders_billing_address', 'orders', 'addresses', ['billing_address_id'], ['id'], ondelete='SET NULL')
    op.drop_column('orders', 'shipping_address')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('orders', sa.Column('shipping_address', sa.TEXT(), autoincrement=False, nullable=True))
    op.drop_constraint('fk_orders_billing_address', 'orders', type_='foreignkey')
    op.drop_constraint('fk_orders_shipping_address', 'orders', type_='foreignkey')
    op.drop_column('orders', 'notes')
    op.drop_column('orders', 'source')
    op.drop_column('orders', 'billing_address_id')
    op.drop_column('orders', 'shipping_address_id')
    op.drop_table('addresses')
