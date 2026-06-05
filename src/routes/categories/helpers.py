from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException
import logging

from src.models.category import Category

logger = logging.getLogger(__name__)


def fetch_subtree_category_rows(db: Session, root_ids: list[int]) -> list[dict]:
    if not root_ids:
        return []

    query = text(
        """
        WITH RECURSIVE category_tree AS (
            SELECT id, name, slug, parent_id
            FROM categories
            WHERE id = ANY(:root_ids)
            UNION ALL
            SELECT child.id, child.name, child.slug, child.parent_id
            FROM categories child
            JOIN category_tree parent ON child.parent_id = parent.id
        )
        SELECT id, name, slug, parent_id
        FROM category_tree
        """
    )
    rows = db.execute(query, {"root_ids": root_ids}).mappings().all()
    return [dict(row) for row in rows]


def get_category_by_id(db: Session, category_id: int) -> Category:
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        logger.warning(f"Category {category_id} not found")
        raise HTTPException(status_code=404, detail="Category not found")
    logger.info(f"Retrieved category {category_id}")
    return category
