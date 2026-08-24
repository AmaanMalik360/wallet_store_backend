from sqlalchemy import CHAR, SmallInteger, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base


class Currency(Base):
    __tablename__ = "currencies"

    code: Mapped[str] = mapped_column(CHAR(3), primary_key=True)
    decimal_places: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=2)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # NOTE (future): Add relationships to product_prices and orders here when
    # you need to query all prices/orders for a given currency.

    def __repr__(self) -> str:
        return f"<Currency(code={self.code}, decimal_places={self.decimal_places}, is_default={self.is_default})>"
