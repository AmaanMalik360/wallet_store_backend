from sqlalchemy import UUID, CHAR, ForeignKey, Integer, String, Text, DateTime, Enum, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from .db import Base
import uuid6
import enum


class OrderStatus(enum.Enum):
    PENDING_PAYMENT = "pending_payment"
    PAID = "paid"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid6.uuid7
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("users.id"), 
        nullable=False
    )
    # total_amount is in minor units of currency_code (paisa for PKR, cents for USD/EUR).
    total_amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    # NOTE (future — multi-currency): When a customer session picks a currency,
    # pass it to create_order(). resolve_price() already accepts currency_code,
    # so unit_amount on each OrderItem will be denominated in orders.currency_code.
    currency_code: Mapped[str] = mapped_column(
        CHAR(3),
        ForeignKey("currencies.code"),
        nullable=False,
        default="PKR",
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus),
        nullable=False,
        default=OrderStatus.PENDING_PAYMENT
    )
    shipping_address_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("addresses.id", ondelete="SET NULL"),
        nullable=True
    )
    billing_address_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("addresses.id", ondelete="SET NULL"),
        nullable=True
    )
    source: Mapped[str] = mapped_column(
        String(20),
        nullable=True
    )
    notes: Mapped[str] = mapped_column(
        Text,
        nullable=True
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
    user: Mapped["User"] = relationship(
        "User",
        back_populates="orders"
    )
    shipping_address: Mapped["Address"] = relationship(
        "Address",
        foreign_keys=[shipping_address_id],
        lazy="joined"
    )
    billing_address: Mapped["Address"] = relationship(
        "Address",
        foreign_keys=[billing_address_id],
        lazy="joined"
    )
    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem", 
        back_populates="order",
        cascade="all, delete-orphan"
    )
    payments: Mapped[list["Payment"]] = relationship(
        "Payment", 
        back_populates="order",
        cascade="all, delete-orphan"
    )
    shipments: Mapped[list["Shipment"]] = relationship(
        "Shipment", 
        back_populates="order",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Order(id={self.id}, user_id={self.user_id}, total_amount={self.total_amount}, currency={self.currency_code}, status={self.status.value})>"


class OrderItem(Base):
    __tablename__ = "order_items"

    order_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("orders.id", ondelete="CASCADE"), 
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
    # unit_amount is a price snapshot in minor units at the time of order creation.
    # It always matches the currency of the parent Order (orders.currency_code).
    unit_amount: Mapped[int] = mapped_column(
        Integer, 
        nullable=False
    )

    # Relationships
    order: Mapped["Order"] = relationship(
        "Order", 
        back_populates="items"
    )
    product: Mapped["Product"] = relationship(
        "Product", 
        back_populates="order_items"
    )

    def __repr__(self) -> str:
        return f"<OrderItem(order_id={self.order_id}, product_id={self.product_id}, quantity={self.quantity}, unit_amount={self.unit_amount})>"
