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
    # Attribute name (e.g., "Color", "Size", "Material")
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
    category_attributes: Mapped[list["CategoryAttribute"]] = relationship(
        "CategoryAttribute",
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
    # Attribute ID (foreign key to attributes table)
    attribute_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("attributes.id"), 
        nullable=False
    )
    # Attribute value (e.g., "Red", "Blue", "Small", "Large", "Cotton", "Leather")
    value: Mapped[str] = mapped_column(
        String(100), 
        nullable=False
    )
    # Optional category scope: NULL = global, set = scoped to specific category
    category_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True
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
        return f"<AttributeValue(id={self.id}, attribute_id={self.attribute_id}, value={self.value}, category_id={self.category_id})>"


class ProductAttributeValue(Base):
    __tablename__ = "product_attribute_values"

    product_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("products.id", ondelete="CASCADE"), 
        primary_key=True
    )
    # Attribute value ID (foreign key to attribute_values table)
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
