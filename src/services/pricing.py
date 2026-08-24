"""
Pricing service — resolves the active product price for a given currency.

Design notes:
  * All monetary amounts are stored and returned in **minor units** of the
    currency (paisa for PKR; cents for USD / EUR; whole units for JPY).
  * resolve_price() is the single entry-point for any code that needs a price.
    Call it from cart, order-creation, and product-listing services.
  * Only synchronous SQLAlchemy Sessions are used here; the FastAPI endpoints
    already inject a synchronous get_db session.

NOTE (future — multi-currency):
  Pass the customer's preferred currency_code (e.g. from the Accept-Currency
  header or user profile) to resolve_price(). No schema changes are needed;
  just insert a ProductPrice row with the new currency_code.

NOTE (future — sale pricing):
  create a ProductPrice row with valid_from / valid_until set. resolve_price()
  already handles this via the date guards below. The permanent price
  (valid_from IS NULL) coexists safely due to the partial unique index
  (uq_product_price_default).

NOTE (future — caching):
  For high-traffic products, wrap the DB query in an LRU or Redis cache
  keyed on (product_id, currency_code). Invalidate on ProductPrice updates.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, and_, or_
from sqlalchemy.orm import Session
from fastapi import HTTPException

from src.models.product_price import ProductPrice


def resolve_price(
    db: Session,
    product_id: UUID,
    currency_code: str = "PKR",
) -> int:
    """
    Return the active price (in minor units) for *product_id* denominated in
    *currency_code*.

    Selection logic (mirrors the partial unique index logic):
      1. is_active = True
      2. currency_code matches
      3. valid_from is NULL  OR  valid_from <= now()      (started)
      4. valid_until is NULL OR  valid_until > now()      (not expired)
      5. Among multiple matching rows (e.g. a scheduled row + permanent row),
         prefer the row with a non-NULL valid_from (scheduled/specific price).

    Raises:
        HTTPException 422 — no active price found; caller should not silently
        return 0 because that would silently create zero-value orders.
    """
    now = datetime.now(timezone.utc)

    stmt = (
        select(ProductPrice)
        .where(
            and_(
                ProductPrice.product_id == product_id,
                ProductPrice.currency_code == currency_code,
                ProductPrice.is_active == True,  # noqa: E712
                or_(
                    ProductPrice.valid_from == None,  # noqa: E711
                    ProductPrice.valid_from <= now,
                ),
                or_(
                    ProductPrice.valid_until == None,  # noqa: E711
                    ProductPrice.valid_until > now,
                ),
            )
        )
        # Prefer scheduled (non-NULL valid_from) over permanent (NULL valid_from)
        # so a sale price takes precedence when both exist in the window.
        # NOTE (future — sale pricing): This ordering is intentional; permanent
        # prices act as a fallback when no scheduled row is active.
        .order_by(ProductPrice.valid_from.desc().nullslast())
        .limit(1)
    )

    row: Optional[ProductPrice] = db.scalars(stmt).first()
    if row is None:
        raise HTTPException(
            status_code=422,
            detail=(
                f"No active {currency_code} price found for product {product_id}. "
                "Ensure a ProductPrice row exists before placing orders."
            ),
        )
    return row.amount


def _active_price_subquery(currency_code: str = "PKR"):
    """
    Return a correlated scalar sub-select that resolves the active price for
    each product row, suitable for use in ORDER BY / WHERE clauses.

    Usage:
        price_sq = _active_price_subquery("PKR").correlate(Product).scalar_subquery()
        query = db.query(Product).order_by(price_sq.asc())

    NOTE (future — multi-currency sorting): Pass the customer's currency_code
    to this function and forward it from the query parameter.
    """
    now = datetime.now(timezone.utc)

    # Import here to avoid circular imports at module level
    from src.models.product import Product  # noqa: F401 (used via correlate)

    return (
        select(ProductPrice.amount)
        .where(
            and_(
                ProductPrice.product_id == Product.id,  # correlated
                ProductPrice.currency_code == currency_code,
                ProductPrice.is_active == True,  # noqa: E712
                or_(
                    ProductPrice.valid_from == None,  # noqa: E711
                    ProductPrice.valid_from <= now,
                ),
                or_(
                    ProductPrice.valid_until == None,  # noqa: E711
                    ProductPrice.valid_until > now,
                ),
            )
        )
        .order_by(ProductPrice.valid_from.desc().nullslast())
        .limit(1)
    )
