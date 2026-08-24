from typing import Optional
from sqlalchemy import UUID, Integer, CHAR, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base
import uuid6


class ProductPrice(Base):
    __tablename__ = "product_prices"

    # UUID generated Python-side — no server_default.
    # PostgreSQL has no native uuid7() function; uuid6.uuid7 runs in Python before INSERT.
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid6.uuid7)
    product_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    currency_code: Mapped[str] = mapped_column(
        CHAR(3), ForeignKey("currencies.code"), nullable=False, default="PKR"
    )
    # amount is in minor units of currency_code (paisa for PKR, cents for USD/EUR).
    # For currencies with 0 decimal places (JPY), the value IS the whole unit.
    # NOTE (future — zero-decimal currencies): When adding JPY or similar, no schema
    # change is needed; just pass amount as whole units and formatPrice() will handle
    # display correctly via Currency.decimal_places.
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # valid_from=None  → effective from creation (permanent/default price)
    # valid_until=None → never expires
    # NOTE (future — sale pricing): Set valid_from/valid_until to schedule time-bound
    # prices. The partial unique index (uq_product_price_default) only covers rows
    # where valid_from IS NULL, so scheduled rows can coexist freely.
    valid_from: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)

    product: Mapped["Product"] = relationship("Product", back_populates="product_prices")

    def __repr__(self) -> str:
        return (
            f"<ProductPrice(product_id={self.product_id}, currency={self.currency_code}, "
            f"amount={self.amount}, active={self.is_active})>"
        )
