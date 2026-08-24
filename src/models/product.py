from typing import Optional
from sqlalchemy import UUID, String, Text, Integer, ForeignKey, DateTime, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from .db import Base
import uuid6


class Product(Base):
    __tablename__ = "products"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid6.uuid7
    )
    title: Mapped[str] = mapped_column(
        Text, 
        nullable=False
    )
    description: Mapped[str] = mapped_column(
        Text, 
        nullable=True
    )
    category_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("categories.id"), 
        nullable=True
    )
    # price column removed — pricing lives in product_prices table.
    # NOTE (future — multi-currency): Add more ProductPrice rows per product,
    # one per currency_code. resolve_price() handles selection by currency.
    stock_quantity: Mapped[int] = mapped_column(
        Integer, 
        nullable=False, 
        default=0
    )
    sku: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        unique=True
    )
    images: Mapped[list[str]] = mapped_column(
        ARRAY(String), 
        nullable=True, 
        default=[]
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now()
    )

    # Relationships
    category: Mapped["Category"] = relationship(
        "Category", 
        back_populates="products"
    )
    product_prices: Mapped[list["ProductPrice"]] = relationship(
        "ProductPrice",
        back_populates="product",
        cascade="all, delete-orphan",
    )
    attribute_values: Mapped[list["ProductAttributeValue"]] = relationship(
        "ProductAttributeValue", 
        back_populates="product",
        cascade="all, delete-orphan"
    )
    cart_items: Mapped[list["CartItem"]] = relationship(
        "CartItem", 
        back_populates="product"
    )
    order_items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem", 
        back_populates="product"
    )

    def __repr__(self) -> str:
        return f"<Product(id={self.id}, title={self.title[:50]}), category={self.category}>"