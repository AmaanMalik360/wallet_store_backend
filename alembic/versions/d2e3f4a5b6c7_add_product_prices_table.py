"""Add product_prices table and drop products.price

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-06-01 00:01:00.000000

NOTE (future — multi-currency pricing):
  When you add a second currency, simply insert additional rows into product_prices
  with the new currency_code. No schema changes are required.

NOTE (future — sale pricing):
  Set valid_from / valid_until on a ProductPrice row to schedule time-bound prices.
  The partial unique index below only covers default prices (valid_from IS NULL), so
  scheduled rows can coexist freely. resolve_price() already handles both filters.

NOTE (future — price history):
  Currently update_product() updates the existing active row in place. When you want
  a full audit trail, change it to: set is_active=False on the old row, then insert
  a new row. The schema already supports this.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'd2e3f4a5b6c7'
down_revision: Union[str, Sequence[str], None] = 'c1d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'product_prices',
        # UUID generated Python-side via uuid6.uuid7 — no server_default needed.
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('product_id', sa.UUID(as_uuid=True), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False),
        sa.Column('currency_code', sa.CHAR(3), sa.ForeignKey('currencies.code'), nullable=False, server_default='PKR'),
        # amount is in minor units of currency_code (paisa for PKR, cents for USD/EUR, etc.)
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        # NULL valid_from  = effective from creation (permanent/default price)
        # NULL valid_until = no expiry
        sa.Column('valid_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('valid_until', sa.DateTime(timezone=True), nullable=True),
    )

    # Partial unique index: only one active default price per product/currency.
    # Standard UNIQUE constraints cannot enforce this when valid_from IS NULL
    # because PostgreSQL treats NULL != NULL in unique constraints.
    op.execute("""
        CREATE UNIQUE INDEX uq_product_price_default
        ON product_prices (product_id, currency_code)
        WHERE valid_from IS NULL AND is_active = TRUE
    """)

    # Drop the old single-currency price column from products.
    op.drop_column('products', 'price')


def downgrade() -> None:
    op.add_column('products', sa.Column('price', sa.Integer(), nullable=False, server_default='0'))
    op.execute("DROP INDEX IF EXISTS uq_product_price_default")
    op.drop_table('product_prices')
