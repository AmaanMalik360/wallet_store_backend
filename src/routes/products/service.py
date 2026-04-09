from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from fastapi import HTTPException
import logging

from . import models
from src.models.product import Product
from src.models.category import Category
from src.models.attribute import ProductAttributeValue, AttributeValue

logger = logging.getLogger(__name__)


def create_product(db: Session, product: models.ProductCreate, image_paths: Optional[List[str]] = None) -> Product:
    try:
        # Create new product
        db_product = Product(
            title=product.title,
            description=product.description,
            category_id=product.category_id,
            price=product.price,
            stock_quantity=product.stock_quantity,
            images=image_paths or product.images or []
        )
        
        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        
        logger.info(f"Created new product: {product.title} with {len(db_product.images)} images")
        return db_product
        
    except Exception as e:
        logger.error(f"Failed to create product {product.title}. Error: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create product")

def get_products(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    category_ids: Optional[List[int]] = None,
    category_slug: Optional[str] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    in_stock: Optional[bool] = None,
    search: Optional[str] = None,
    sort_by: Optional[str] = None,
    attribute_value_ids: Optional[List[int]] = None
) -> Dict[str, Any]:
    try:
        query = db.query(Product).options(
            joinedload(Product.category),
            joinedload(Product.attribute_values)
        )

        if search:
            query = query.filter(
                Product.title.ilike(f"%{search}%") |
                Product.description.ilike(f"%{search}%")
            )

        # Multiple explicit category IDs (from subcategory filter)
        if category_ids:
            all_ids: set[int] = set()
            for cid in category_ids:
                all_ids.add(cid)
                all_ids.update(Category.get_all_descendant_ids(db, cid))
            query = query.filter(Product.category_id.in_(all_ids))

        # Slug-based filter (page-level, broader scope)
        elif category_slug:
            category = db.query(Category).filter(Category.slug == category_slug).first()
            if category:
                descendant_ids = Category.get_all_descendant_ids(db, category.id)
                query = query.filter(Product.category_id.in_([category.id] + descendant_ids))

        if min_price is not None:
            query = query.filter(Product.price >= min_price)
        if max_price is not None:
            query = query.filter(Product.price <= max_price)
        if in_stock is not None:
            query = query.filter(
                Product.stock_quantity > 0 if in_stock else Product.stock_quantity == 0
            )

        # Attribute filtering with AND semantics across different attributes
        if attribute_value_ids:
            # Group attribute value IDs by their attribute_id for proper OR within same attribute, AND across attributes
            value_to_attr = {}
            attr_values = db.query(AttributeValue).filter(
                AttributeValue.id.in_(attribute_value_ids)
            ).all()
            
            for av in attr_values:
                if av.attribute_id not in value_to_attr:
                    value_to_attr[av.attribute_id] = []
                value_to_attr[av.attribute_id].append(av.id)
            
            # For each attribute, product must have at least one of the selected values (OR within attribute)
            # Across attributes, product must match all (AND across attributes)
            for attr_id, val_ids in value_to_attr.items():
                query = query.filter(
                    Product.id.in_(
                        db.query(ProductAttributeValue.product_id)
                        .filter(ProductAttributeValue.attribute_value_id.in_(val_ids))
                    )
                )

        # Sorting
        if sort_by == "price-low":
            query = query.order_by(Product.price.asc())
        elif sort_by == "price-high":
            query = query.order_by(Product.price.desc())
        elif sort_by == "newest":
            query = query.order_by(Product.created_at.desc())
        elif sort_by == "name":
            query = query.order_by(Product.title.asc())
        else:  # featured / default
            query = query.order_by(Product.created_at.desc())

        # Get total count after all filters and sorting, before pagination
        total = query.count()

        products = query.offset(skip).limit(limit).all()
        logger.info(f"Retrieved {len(products)} products out of {total} total")
        return {
            "data": products,
            "total": total,
            "skip": skip,
            "limit": limit
        }

    except Exception as e:
        logger.error(f"Failed to retrieve products. Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve products")

def get_product_by_id(db: Session, product_id: UUID) -> Product:
    """Get a specific product by ID with category information"""
    product = db.query(Product).options(
        joinedload(Product.category)
    ).filter(Product.id == product_id).first()
    
    if not product:
        logger.warning(f"Product {product_id} not found")
        raise HTTPException(status_code=404, detail="Product not found")
    
    logger.info(f"Retrieved product {product_id}")
    return product


def update_product(db: Session, product_id: UUID, update_data: dict) -> Product:
    try:
        product = get_product_by_id(db, product_id)
        
        # Update fields based on provided data
        for field, value in update_data.items():
            setattr(product, field, value)
        
        db.commit()
        db.refresh(product)
        
        logger.info(f"Updated product {product_id} with fields: {list(update_data.keys())}")
        return product
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update product {product_id}. Error: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update product")


def delete_product(db: Session, product_id: UUID) -> None:
    try:
        product = get_product_by_id(db, product_id)
        
        db.delete(product)
        db.commit()
        logger.info(f"Deleted product {product_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete product {product_id}. Error: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete product")


