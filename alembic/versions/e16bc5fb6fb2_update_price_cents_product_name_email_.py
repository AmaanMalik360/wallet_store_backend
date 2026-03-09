"""Update price_cents(product), name, email(user)

Revision ID: e16bc5fb6fb2
Revises: 8376bdfa5dad
Create Date: 2026-03-02 01:52:40.123346

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e16bc5fb6fb2'
down_revision: Union[str, Sequence[str], None] = '8376bdfa5dad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade() -> None:
    # users: rename password_hash -> password
    op.alter_column(
        "users",
        "password_hash",
        new_column_name="password",
        existing_type=sa.String(length=255),
        existing_nullable=False,
    )

    # users: make password nullable
    op.alter_column(
        "users",
        "password",
        existing_type=sa.String(length=255),
        nullable=True,
    )

    # users: make email nullable
    op.alter_column(
        "users",
        "email",
        existing_type=sa.String(length=255),
        nullable=True,
    )

    # products: rename price_cents -> price
    op.alter_column(
        "products",
        "price_cents",
        new_column_name="price",
        existing_type=sa.Integer(),
        existing_nullable=False,
    )

    # products: add images (postgres text/varchar array)
    op.add_column(
        "products",
        sa.Column("images", postgresql.ARRAY(sa.String()), nullable=True, server_default=sa.text("'{}'")),
    )


def downgrade() -> None:
    # products: drop images
    op.drop_column("products", "images")

    # products: rename price -> price_cents
    op.alter_column(
        "products",
        "price",
        new_column_name="price_cents",
        existing_type=sa.Integer(),
        existing_nullable=False,
    )

    # users: make email NOT NULL again
    op.alter_column(
        "users",
        "email",
        existing_type=sa.String(length=255),
        nullable=False,
    )

    # users: make password NOT NULL again
    op.alter_column(
        "users",
        "password",
        existing_type=sa.String(length=255),
        nullable=False,
    )

    # users: rename password -> password_hash
    op.alter_column(
        "users",
        "password",
        new_column_name="password_hash",
        existing_type=sa.String(length=255),
        existing_nullable=False,
    )