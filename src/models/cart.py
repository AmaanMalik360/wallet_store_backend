from sqlalchemy import UUID, ForeignKey, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from .db import Base
import uuid


class Cart(Base):
    __tablename__ = "carts"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="SET NULL"), 
        nullable=True
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User", 
        back_populates="cart"
    )
    items: Mapped[list["CartItem"]] = relationship(
        "CartItem", 
        back_populates="cart",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Cart(id={self.id}, user_id={self.user_id})>"


class CartItem(Base):
    __tablename__ = "cart_items"

    cart_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("carts.id", ondelete="CASCADE"), 
        primary_key=True
    )
    product_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("products.id"), 
        primary_key=True
    )
    quantity: Mapped[int] = mapped_column(
        Integer, 
        nullable=False
    )
    added_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )

    # Relationships
    cart: Mapped["Cart"] = relationship(
        "Cart", 
        back_populates="items"
    )
    product: Mapped["Product"] = relationship(
        "Product", 
        back_populates="cart_items"
    )

    def __repr__(self) -> str:
        return f"<CartItem(cart_id={self.cart_id}, product_id={self.product_id}, quantity={self.quantity})>"
