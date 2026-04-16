from sqlalchemy import Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base


class CategoryAttribute(Base):
    __tablename__ = "category_attributes"

    category_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("categories.id", ondelete="CASCADE"),
        primary_key=True
    )
    attribute_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("attributes.id", ondelete="CASCADE"),
        primary_key=True
    )

    # Relationships
    category: Mapped["Category"] = relationship(
        "Category",
        back_populates="category_attributes"
    )
    attribute: Mapped["Attribute"] = relationship(
        "Attribute",
        back_populates="category_attributes"
    )

    def __repr__(self) -> str:
        return f"<CategoryAttribute(category_id={self.category_id}, attribute_id={self.attribute_id})>"
