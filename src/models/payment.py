from sqlalchemy import UUID, ForeignKey, Integer, String, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from .db import Base
import uuid
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
        default=uuid.uuid4
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
    amount_cents: Mapped[int] = mapped_column(
        Integer, 
        nullable=False
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
        return f"<Payment(id={self.id}, order_id={self.order_id}, gateway={self.gateway}, amount_cents={self.amount_cents}, status={self.status.value})>"
