from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException
import logging

from . import models
from src.models.product import Product
from src.models.category import Category

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
    category_id: Optional[int] = None,
    category_slug: Optional[str] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    in_stock: Optional[bool] = None,
    search: Optional[str] = None
) -> List[Product]:
    """Get products with optional filtering, search, and pagination"""
    try:
        query = db.query(Product).options(joinedload(Product.category))
        
        # Apply search filter
        if search is not None and search != "":
            query = query.filter(
                Product.title.ilike(f"%{search}%") | 
                Product.description.ilike(f"%{search}%")
            )
        
        # Apply filters
        if category_id is not None :
            query = query.filter(Product.category_id == category_id)
        
        if category_slug is not None and category_slug != "":
            # Find the category by slug
            category = db.query(Category).filter(Category.slug == category_slug).first()
            if category:
                # Get all descendant category IDs recursively using classmethod
                descendant_ids = Category.get_all_descendant_ids(db, category.id)
                # Include the parent category ID and all descendant IDs
                all_category_ids = [category.id] + descendant_ids
                # Filter products by all category IDs in the hierarchy
                query = query.filter(Product.category_id.in_(all_category_ids))
        
        if min_price is not None:
            query = query.filter(Product.price >= min_price)
        
        if max_price is not None:
            query = query.filter(Product.price <= max_price)
        
        if in_stock is not None:
            if in_stock:
                query = query.filter(Product.stock_quantity > 0)
            else:
                query = query.filter(Product.stock_quantity == 0)
        
        # Apply pagination
        products = query.offset(skip).limit(limit).all()
        
        search_info = f" (search='{search}')" if search else ""
        logger.info(f"Retrieved {len(products)} products (skip={skip}, limit={limit}){search_info}")
        if products:
            logger.info(f"First 3 products: {products[:3]}")
        return products
        
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


