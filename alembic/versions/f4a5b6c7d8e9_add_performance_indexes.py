"""Add performance indexes, carts.user_id uniqueness, and carts FK cascade

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-08-28 00:01:00.000000

Indexing strategy (see .devin/rules/database.md):
  * PostgreSQL does not auto-index FK columns — every FK used in WHERE/JOIN
    gets an explicit index here.
  * Composite indexes match the real filter+sort patterns:
      orders(user_id, created_at)  — customer order list
      orders(status, created_at)   — admin status-filtered list
  * ix_product_prices_lookup covers resolve_prices() (DISTINCT ON product_id);
    uq_product_price_default stays a data-integrity constraint, not a lookup index.
  * ix_users_guest_expiry is a partial index over guest rows only, for the
    future expired-guest cleanup job.
  * NO pg_trgm indexes — ILIKE '%term%' search stays a seq scan while the
    product/user dataset is small. Revisit at scale.

carts.user_id changes:
  * UNIQUE — one cart per user (User.cart is uselist=False). A dedup DELETE
    runs first in case existing data already violates the invariant.
  * FK ondelete SET NULL -> CASCADE — deleting a user (expired guests)
    removes the cart; cart_items cascade from there.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'f4a5b6c7d8e9'
down_revision: Union[str, Sequence[str], None] = 'e3f4a5b6c7d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- carts.user_id: dedup, CASCADE FK, UNIQUE ---------------------------

    # Keep the earliest-created cart per user; cart_items rows on discarded
    # carts are removed by the existing cart_items.cart_id ON DELETE CASCADE.
    op.execute("""
        DELETE FROM carts
        WHERE id IN (
            SELECT id FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY user_id
                           ORDER BY created_at ASC, id ASC
                       ) AS rn
                FROM carts
                WHERE user_id IS NOT NULL
            ) ranked
            WHERE rn > 1
        )
    """)

    op.drop_constraint('carts_user_id_fkey', 'carts', type_='foreignkey')
    op.create_foreign_key(
        'carts_user_id_fkey', 'carts', 'users',
        ['user_id'], ['id'], ondelete='CASCADE',
    )
    op.create_unique_constraint('uq_carts_user_id', 'carts', ['user_id'])

    # --- FK indexes (hot query paths) ---------------------------------------

    op.create_index('ix_products_category_id', 'products', ['category_id'])
    op.create_index('ix_products_created_at', 'products', ['created_at'])
    op.create_index('ix_categories_parent_id', 'categories', ['parent_id'])
    op.create_index('ix_addresses_user_id', 'addresses', ['user_id'])
    op.create_index('ix_attribute_values_attribute_id', 'attribute_values', ['attribute_id'])
    op.create_index('ix_attribute_values_category_id', 'attribute_values', ['category_id'])
    op.create_index(
        'ix_product_attr_values_attr_value_id',
        'product_attribute_values',
        ['attribute_value_id'],
    )
    op.create_index('ix_shipments_order_id', 'shipments', ['order_id'])
    op.create_index('ix_payments_order_id', 'payments', ['order_id'])

    # --- Order list queries: filter + sort in one index scan ----------------

    op.create_index('ix_orders_user_id_created', 'orders', ['user_id', 'created_at'])
    op.create_index('ix_orders_status_created', 'orders', ['status', 'created_at'])

    # --- resolve_prices() covering index ------------------------------------
    # Column order matches the WHERE + DISTINCT ON: equality cols first,
    # then the range/order cols used for best-row selection.
    op.create_index(
        'ix_product_prices_lookup',
        'product_prices',
        ['product_id', 'currency_code', 'is_active', 'valid_from', 'valid_until'],
    )

    # --- Expired-guest cleanup (partial: guest rows only) -------------------
    # Supports: WHERE is_guest = TRUE AND guest_expires_at < now()
    op.execute("""
        CREATE INDEX ix_users_guest_expiry
        ON users (guest_expires_at)
        WHERE is_guest = TRUE
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_users_guest_expiry")
    op.drop_index('ix_product_prices_lookup', table_name='product_prices')
    op.drop_index('ix_orders_status_created', table_name='orders')
    op.drop_index('ix_orders_user_id_created', table_name='orders')
    op.drop_index('ix_payments_order_id', table_name='payments')
    op.drop_index('ix_shipments_order_id', table_name='shipments')
    op.drop_index('ix_product_attr_values_attr_value_id', table_name='product_attribute_values')
    op.drop_index('ix_attribute_values_category_id', table_name='attribute_values')
    op.drop_index('ix_attribute_values_attribute_id', table_name='attribute_values')
    op.drop_index('ix_addresses_user_id', table_name='addresses')
    op.drop_index('ix_categories_parent_id', table_name='categories')
    op.drop_index('ix_products_created_at', table_name='products')
    op.drop_index('ix_products_category_id', table_name='products')

    op.drop_constraint('uq_carts_user_id', 'carts', type_='unique')
    op.drop_constraint('carts_user_id_fkey', 'carts', type_='foreignkey')
    op.create_foreign_key(
        'carts_user_id_fkey', 'carts', 'users',
        ['user_id'], ['id'], ondelete='SET NULL',
    )
