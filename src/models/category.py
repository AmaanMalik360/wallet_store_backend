from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base
from slugify import slugify
from sqlalchemy.orm import Session

class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(
        Integer, 
        primary_key=True
    )
    name: Mapped[str] = mapped_column(
        String(100), 
        nullable=False
    )
    slug: Mapped[str] = mapped_column(
        String(250),
        nullable=False,
        unique=True
    )
    parent_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("categories.id", ondelete="SET NULL"), 
        nullable=True
    )

    # Self-referential relationship for hierarchy
    parent: Mapped["Category"] = relationship(
        "Category", 
        remote_side="Category.id", 
        back_populates="children"
    )
    children: Mapped[list["Category"]] = relationship(
        "Category", 
        back_populates="parent",
        cascade="all, delete-orphan"
    )

    @staticmethod
    def generate_slug(name: str) -> str:
        """Generate URL-friendly slug from name"""
        return slugify(name)

    @classmethod
    def create(cls, db: Session, name: str, parent_id: int = None) -> "Category":
        """Create a new category with auto-generated slug"""
        category = cls(
            name=name,
            slug=cls.generate_slug(name),
            parent_id=parent_id
        )
        db.add(category)
        db.flush()
        return category

    @classmethod
    def get_all_descendant_ids(cls, db: Session, category_id: int) -> list[int]:
        """Get all descendant category IDs recursively"""
        category = db.query(cls).filter(cls.id == category_id).first()
        if not category:
            return []
        
        descendant_ids = []
        for child in category.children:
            descendant_ids.append(child.id)
            descendant_ids.extend(cls.get_all_descendant_ids(db, child.id))
        return descendant_ids

    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name={self.name}, parent_id={self.parent_id})>"
