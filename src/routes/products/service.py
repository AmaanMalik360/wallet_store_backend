from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from fastapi import HTTPException
import logging

from . import models
from .sku_generator import generate_sku
from src.models.product import Product
from src.models.category import Category
from src.models.attribute import ProductAttributeValue, AttributeValue

logger = logging.getLogger(__name__)


def _get_product_orm(db: Session, product_id: UUID) -> Product:
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


def _build_product_response(product: Product) -> models.ProductWithCategory:
    return models.ProductWithCategory(
        id=product.id,
        title=product.title,
        description=product.description,
        category_id=product.category_id,
        price=product.price,
        stock_quantity=product.stock_quantity,
        sku=product.sku,
        images=product.images or [],
        created_at=product.created_at,
        updated_at=product.updated_at,
        category=models.CategoryInProduct.model_validate(product.category) if product.category else None,
        attributes=[
            models.ProductAttribute(
                value_id=pav.attribute_value.id,
                attribute_id=pav.attribute_value.attribute_id,
                name=pav.attribute_value.attribute.name,
                value=pav.attribute_value.value,
            )
            for pav in product.attribute_values
            if pav.attribute_value and pav.attribute_value.attribute
        ],
    )


def create_product(
    db: Session,
    product: models.ProductCreate,
    image_paths: Optional[List[str]] = None,
    attribute_value_ids: Optional[List[int]] = None
) -> Product:
    try:
        db_product = Product(
            title=product.title,
            description=product.description,
            category_id=product.category_id,
            price=product.price,
            stock_quantity=product.stock_quantity,
            sku=product.sku,
            images=image_paths or product.images or []
        )

        db.add(db_product)
        db.flush()

        if not db_product.sku:
            cat = None
            if product.category_id:
                cat = db.query(Category).options(
                    joinedload(Category.parent)
                ).filter(Category.id == product.category_id).first()
            db_product.sku = generate_sku(db, cat)

        if attribute_value_ids:
            for av_id in attribute_value_ids:
                pav = ProductAttributeValue(
                    product_id=db_product.id,
                    attribute_value_id=av_id
                )
                db.add(pav)

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
) -> Dict[str, Any]:  # data: List[models.ProductWithCategory]
    try:
        query = db.query(Product).options(
            joinedload(Product.category),
            joinedload(Product.attribute_values)
            .joinedload(ProductAttributeValue.attribute_value)
            .joinedload(AttributeValue.attribute)
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
            "data": [_build_product_response(p) for p in products],
            "total": total,
            "skip": skip,
            "limit": limit
        }

    except Exception as e:
        logger.error(f"Failed to retrieve products. Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve products")

def get_product_by_id(db: Session, product_id: UUID) -> models.ProductWithCategory:
    """Get a specific product by ID with category and flat attributes"""
    product = db.query(Product).options(
        joinedload(Product.category),
        joinedload(Product.attribute_values)
        .joinedload(ProductAttributeValue.attribute_value)
        .joinedload(AttributeValue.attribute)
    ).filter(Product.id == product_id).first()

    if not product:
        logger.warning(f"Product {product_id} not found")
        raise HTTPException(status_code=404, detail="Product not found")

    logger.info(f"Retrieved product {product_id}")
    return _build_product_response(product)


def update_product(db: Session, product_id: UUID, update_data: dict) -> Product:
    try:
        product = _get_product_orm(db, product_id)
        
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
        product = _get_product_orm(db, product_id)
        
        db.delete(product)
        db.commit()
        logger.info(f"Deleted product {product_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete product {product_id}. Error: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete product")


