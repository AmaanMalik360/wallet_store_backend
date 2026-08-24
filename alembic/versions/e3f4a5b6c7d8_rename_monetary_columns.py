"""Rename monetary columns and add currency_code to orders, order_items, payments

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-06-01 00:02:00.000000

Column renames use currency-agnostic names (_amount instead of _cents/_paise):
  orders.total_cents      → orders.total_amount
  order_items.price_cents → order_items.unit_amount
  payments.amount_cents   → payments.amount

currency_code is added to orders and payments (NOT order_items — it always
inherits from the parent order).

NOTE (future — multi-currency orders):
  When a customer session sets a preferred currency, pass it to create_order()
  and store it in orders.currency_code. resolve_price() already accepts
  currency_code as a parameter. The order_items.unit_amount will then be
  denominated in that currency.

NOTE (future — Stripe/Razorpay):
  payments.currency_code is required by all major payment gateways when
  creating a payment intent. This column must exist before any gateway
  integration is wired up.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'e3f4a5b6c7d8'
down_revision: Union[str, Sequence[str], None] = 'd2e3f4a5b6c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # orders: rename total_cents → total_amount, add currency_code
    op.alter_column('orders', 'total_cents', new_column_name='total_amount')
    op.add_column('orders', sa.Column(
        'currency_code', sa.CHAR(3),
        sa.ForeignKey('currencies.code'),
        nullable=False,
        server_default='PKR',
    ))

    # order_items: rename price_cents → unit_amount (no currency_code — inherits from order)
    op.alter_column('order_items', 'price_cents', new_column_name='unit_amount')

    # payments: rename amount_cents → amount, add currency_code
    op.alter_column('payments', 'amount_cents', new_column_name='amount')
    op.add_column('payments', sa.Column(
        'currency_code', sa.CHAR(3),
        sa.ForeignKey('currencies.code'),
        nullable=False,
        server_default='PKR',
    ))


def downgrade() -> None:
    op.drop_column('payments', 'currency_code')
    op.alter_column('payments', 'amount', new_column_name='amount_cents')
    op.alter_column('order_items', 'unit_amount', new_column_name='price_cents')
    op.drop_column('orders', 'currency_code')
    op.alter_column('orders', 'total_amount', new_column_name='total_cents')
