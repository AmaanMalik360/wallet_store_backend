from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException
import logging
from collections import defaultdict

from . import models
from src.models.category import Category
from src.routes.attributes.service import build_filterable_attributes_for_category_map

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


def build_category_hierarchy_from_maps(
    category_id: int,
    categories_by_id: dict[int, dict],
    children_by_parent: dict[int | None, list[int]],
    attrs_by_category_id: dict[int, list[dict]],
) -> models.CategoryData:
    category = categories_by_id[category_id]
    children = [
        build_category_hierarchy_from_maps(
            child_id,
            categories_by_id=categories_by_id,
            children_by_parent=children_by_parent,
            attrs_by_category_id=attrs_by_category_id,
        )
        for child_id in children_by_parent.get(category_id, [])
    ]

    return models.CategoryData(
        id=category["id"],
        name=category["name"],
        slug=category["slug"],
        parent_id=category["parent_id"],
        children=children,
        filterable_attributes=attrs_by_category_id.get(category_id, []),
    )


def collect_subtree_rows_from_orm(category: Category) -> list[dict]:
    rows: list[dict] = []

    def _walk(node: Category):
        rows.append(
            {
                "id": node.id,
                "name": node.name,
                "slug": node.slug,
                "parent_id": node.parent_id,
            }
        )
        for child in node.children:
            _walk(child)

    _walk(category)
    return rows


def build_category_trees_from_subtree_rows(
    db: Session,
    root_ids: list[int],
    subtree_rows: list[dict],
    include_attributes: bool,
) -> list[models.CategoryData]:
    if not root_ids:
        return []

    categories_by_id = {row["id"]: row for row in subtree_rows}
    children_by_parent: dict[int | None, list[int]] = defaultdict(list)
    for row in subtree_rows:
        children_by_parent[row["parent_id"]].append(row["id"])

    attrs_by_category_id: dict[int, list[dict]] = {}
    if include_attributes:
        attrs_by_category_id = build_filterable_attributes_for_category_map(db, categories_by_id)

    return [
        build_category_hierarchy_from_maps(
            category_id=root_id,
            categories_by_id=categories_by_id,
            children_by_parent=children_by_parent,
            attrs_by_category_id=attrs_by_category_id,
        )
        for root_id in root_ids
        if root_id in categories_by_id
    ]


def build_category_hierarchy(
    category: Category,
    db: Optional[Session] = None,
    include_attributes: bool = False
) -> models.CategoryData:
    """Build category hierarchy via map-based tree builder."""
    subtree_rows = collect_subtree_rows_from_orm(category)

    if db is None:
        categories_by_id = {row["id"]: row for row in subtree_rows}
        children_by_parent: dict[int | None, list[int]] = defaultdict(list)
        for row in subtree_rows:
            children_by_parent[row["parent_id"]].append(row["id"])

        return build_category_hierarchy_from_maps(
            category_id=category.id,
            categories_by_id=categories_by_id,
            children_by_parent=children_by_parent,
            attrs_by_category_id={},
        )

    trees = build_category_trees_from_subtree_rows(
        db=db,
        root_ids=[category.id],
        subtree_rows=subtree_rows,
        include_attributes=include_attributes,
    )
    return trees[0]


def create_category(db: Session, category: models.CategoryCreate) -> models.CategoryData:
    try:
        # Check if category name already exists
        existing_category = db.query(Category).filter(Category.name == category.name).first()
        if existing_category:
            raise HTTPException(
                status_code=400,
                detail="Category name already exists"
            )
        
        # Create new category
        db_category = Category.create(db, category.name, category.parent_id)
        
        db.commit()
        db.refresh(db_category)
        
        logger.info(f"Created new category: {category.name}")
        return build_category_hierarchy(db_category, db=db, include_attributes=False)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create category {category.name}. Error: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create category")


def get_categories(db: Session, slug: Optional[str] = None, skip: int = 0, limit: int = 100) -> List[models.CategoryData]:
    """Get categories - all parent categories with children if no slug, or specific category with children if slug provided"""
    try:
        if slug:
            # Get specific category by slug (pagination ignored for specific category)
            category = db.query(Category).filter(Category.slug == slug).first()
            if not category:
                raise HTTPException(status_code=404, detail="Category not found")

            root_ids = [category.id]
            subtree_rows = fetch_subtree_category_rows(db, root_ids)
            trees = build_category_trees_from_subtree_rows(
                db=db,
                root_ids=root_ids,
                subtree_rows=subtree_rows,
                include_attributes=True,
            )
            result = trees[0].children if trees else []
            logger.info(f"Retrieved category with slug: {slug}")
        else:
            # Get paginated parent categories (categories with no parent)
            parent_categories = db.query(Category).filter(
                Category.parent_id.is_(None)
            ).offset(skip).limit(limit).all()
            root_ids = [category.id for category in parent_categories]

            subtree_rows = fetch_subtree_category_rows(db, root_ids)
            result = build_category_trees_from_subtree_rows(
                db=db,
                root_ids=root_ids,
                subtree_rows=subtree_rows,
                include_attributes=True,
            )
            logger.info(f"Retrieved {len(parent_categories)} parent categories (skip={skip}, limit={limit})")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve categories. Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve categories")


def get_category_by_id(db: Session, category_id: int) -> Category:
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        logger.warning(f"Category {category_id} not found")
        raise HTTPException(status_code=404, detail="Category not found")
    logger.info(f"Retrieved category {category_id}")
    return category


def update_category(db: Session, category_id: int, category_update: models.CategoryUpdate) -> models.CategoryData:
    try:
        category = get_category_by_id(db, category_id)
        
        update_data = category_update.model_dump(exclude_unset=True)
        
        # Check if name is being updated and if it already exists
        if "name" in update_data:
            existing_category = db.query(Category).filter(
                Category.name == update_data["name"],
                Category.id != category_id
            ).first()
            if existing_category:
                raise HTTPException(
                    status_code=400,
                    detail="Category name already exists"
                )
        
        for field, value in update_data.items():
            setattr(category, field, value)
        
        # Update slug if name was changed
        if "name" in update_data:
            category.slug = Category.generate_slug(update_data["name"])
        
        db.commit()
        db.refresh(category)
        
        logger.info(f"Updated category {category_id}")
        return build_category_hierarchy(category, db=db, include_attributes=False)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update category {category_id}. Error: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update category")


def delete_category(db: Session, category_id: int) -> None:
    try:
        category = get_category_by_id(db, category_id)
        
        # Check if category has children
        if category.children:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete category with children. Delete children first."
            )
        
        db.delete(category)
        db.commit()
        logger.info(f"Deleted category {category_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete category {category_id}. Error: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete category")
