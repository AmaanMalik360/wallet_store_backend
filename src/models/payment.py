from sqlalchemy import UUID, CHAR, ForeignKey, Integer, String, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from .db import Base
import uuid6
import enum


class PaymentStatus(enum.Enum):
    INITIATED = "initiated"
    SUCCESS = "success"
    FAILED = "failed"


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid6.uuid7
    )
    order_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("orders.id", ondelete="CASCADE"), 
        nullable=False
    )
    gateway: Mapped[str] = mapped_column(
        String(50), 
        nullable=False
    )
    payment_intent_id: Mapped[str] = mapped_column(
        String(100), 
        nullable=True, 
        unique=True
    )
    # amount is in minor units of currency_code (paisa for PKR, cents for USD/EUR).
    amount: Mapped[int] = mapped_column(
        Integer, 
        nullable=False
    )
    # NOTE (future — Stripe/Razorpay): payment gateways require currency on the
    # payment intent. Pass self.currency_code directly to the gateway API call.
    currency_code: Mapped[str] = mapped_column(
        CHAR(3),
        ForeignKey("currencies.code"),
        nullable=False,
        default="PKR",
    )
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus), 
        nullable=False
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
    order: Mapped["Order"] = relationship(
        "Order", 
        back_populates="payments"
    )

    def __repr__(self) -> str:
        return f"<Payment(id={self.id}, order_id={self.order_id}, gateway={self.gateway}, amount={self.amount}, currency={self.currency_code}, status={self.status.value})>"
