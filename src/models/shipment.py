from sqlalchemy import UUID, ForeignKey, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base
import uuid


class Shipment(Base):
    __tablename__ = "shipments"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    order_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("orders.id"), 
        nullable=False
    )
    carrier: Mapped[str] = mapped_column(
        String(50), 
        nullable=True
    )
    tracking_number: Mapped[str] = mapped_column(
        String(100), 
        nullable=True
    )
    shipped_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), 
        nullable=True
    )
    delivered_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), 
        nullable=True
    )

    # Relationships
    order: Mapped["Order"] = relationship(
        "Order", 
        back_populates="shipments"
    )

    def __repr__(self) -> str:
        return f"<Shipment(id={self.id}, order_id={self.order_id}, carrier={self.carrier}, tracking_number={self.tracking_number})>"
