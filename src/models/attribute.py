from sqlalchemy import UUID, Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base
import uuid


class Attribute(Base):
    __tablename__ = "attributes"

    id: Mapped[int] = mapped_column(
        Integer, 
        primary_key=True
    )
    name: Mapped[str] = mapped_column(
        String(50), 
        nullable=False, 
        unique=True
    )

    # Relationships
    values: Mapped[list["AttributeValue"]] = relationship(
        "AttributeValue", 
        back_populates="attribute",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Attribute(id={self.id}, name={self.name})>"


class AttributeValue(Base):
    __tablename__ = "attribute_values"

    id: Mapped[int] = mapped_column(
        Integer, 
        primary_key=True
    )
    attribute_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("attributes.id"), 
        nullable=False
    )
    value: Mapped[str] = mapped_column(
        String(100), 
        nullable=False
    )

    # Relationships
    attribute: Mapped["Attribute"] = relationship(
        "Attribute", 
        back_populates="values"
    )
    product_values: Mapped[list["ProductAttributeValue"]] = relationship(
        "ProductAttributeValue", 
        back_populates="attribute_value"
    )

    def __repr__(self) -> str:
        return f"<AttributeValue(id={self.id}, attribute_id={self.attribute_id}, value={self.value})>"


class ProductAttributeValue(Base):
    __tablename__ = "product_attribute_values"

    product_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("products.id", ondelete="CASCADE"), 
        primary_key=True
    )
    attribute_value_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("attribute_values.id"), 
        primary_key=True
    )

    # Relationships
    product: Mapped["Product"] = relationship(
        "Product", 
        back_populates="attribute_values"
    )
    attribute_value: Mapped["AttributeValue"] = relationship(
        "AttributeValue", 
        back_populates="product_values"
    )

    def __repr__(self) -> str:
        return f"<ProductAttributeValue(product_id={self.product_id}, attribute_value_id={self.attribute_value_id})>"
