from sqlalchemy import Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from typing import TYPE_CHECKING
from .db import Base

if TYPE_CHECKING:
    from .role import RolePermission


class Permission(Base):
    """
    Permissions follow the 'resource:action' naming convention.
    Examples:
        - products:create
        - products:read
        - products:update
        - products:delete
        - orders:read
        - orders:update
        - users:manage
        - admin:access
    """
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(
        String(100), 
        nullable=False, 
        unique=True
    )
    description: Mapped[str] = mapped_column(
        String(255), 
        nullable=True
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )

    # Relationships
    role_permissions: Mapped[list["RolePermission"]] = relationship(
        "RolePermission",
        back_populates="permission",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Permission(id={self.id}, name={self.name})>"
