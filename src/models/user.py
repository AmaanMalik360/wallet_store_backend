from sqlalchemy import UUID, String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from .db import Base
import uuid


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), 
        unique=True, 
        nullable=True,
        index=True
    )
    password: Mapped[str] = mapped_column(
        String(255), 
        nullable=True
    )
    name: Mapped[str] = mapped_column(
        String(100), 
        nullable=True
    )
    is_guest: Mapped[bool] = mapped_column(
        Boolean, 
        nullable=False, 
        default=False
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

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, is_guest={self.is_guest})>"
