from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException
import logging

from . import models
from src.models.category import Category
from src.routes.attributes.service import get_attributes_for_category

logger = logging.getLogger(__name__)


def build_category_hierarchy(
    category: Category,
    db: Optional[Session] = None,
    include_attributes: bool = False
) -> models.CategoryData:
    """Recursively build category hierarchy with children"""
    children = [build_category_hierarchy(child, db=db, include_attributes=include_attributes) for child in category.children]
    
    # Get filterable attributes for this category (returns list of dicts with name and values)
    filterable_attributes = []
    if include_attributes and db is not None:
        filterable_attributes = get_attributes_for_category(db, category.slug)
    
    return models.CategoryData(
        id=category.id,
        name=category.name,
        slug=category.slug,
        parent_id=category.parent_id,
        children=children,
        filterable_attributes=filterable_attributes
    )


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
            
            result = [build_category_hierarchy(category, db=db, include_attributes=True)]
            result = result[0].children
            logger.info(f"Retrieved category with slug: {slug}")
        else:
            # Get paginated parent categories (categories with no parent)
            parent_categories = db.query(Category).filter(
                Category.parent_id.is_(None)
            ).offset(skip).limit(limit).all()
            result = [build_category_hierarchy(category, db=db, include_attributes=True) for category in parent_categories]
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
