from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from fastapi import HTTPException
import logging

from . import models
from .sku_generator import generate_sku
from src.models.product import Product
from src.models.product_price import ProductPrice
from src.models.category import Category
from src.models.attribute import ProductAttributeValue, AttributeValue
from src.services.pricing import _active_price_subquery

logger = logging.getLogger(__name__)

# Default currency used throughout the single-currency MVP.
# NOTE (future — multi-currency): Accept currency_code as a function parameter
# (e.g. from an Accept-Currency header) and propagate it to _active_price and
# _build_product_response instead of using this constant.
_DEFAULT_CURRENCY = "PKR"


def _get_product_orm(db: Session, product_id: UUID) -> Product:
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


def _resolve_active_price(product: Product, currency_code: str = _DEFAULT_CURRENCY) -> int:
    """
    Resolve the active price from the eagerly-loaded product_prices relationship.
    Returns 0 if no active price is found (safe for display; order creation raises
    instead via resolve_price()).
    """
    now = datetime.now(timezone.utc)
    for pp in product.product_prices:
        if (
            pp.is_active
            and pp.currency_code == currency_code
            and (pp.valid_from is None or pp.valid_from <= now)
            and (pp.valid_until is None or pp.valid_until > now)
        ):
            return pp.amount
    return 0


def _build_product_response(product: Product) -> models.ProductWithCategory:
    price_amount = _resolve_active_price(product)
    return models.ProductWithCategory(
        id=product.id,
        title=product.title,
        description=product.description,
        category_id=product.category_id,
        price_amount=price_amount,
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


def _product_query_base(db: Session):
    """Base query with all necessary joinedloads."""
    return db.query(Product).options(
        joinedload(Product.product_prices),
        joinedload(Product.category),
        joinedload(Product.attribute_values)
        .joinedload(ProductAttributeValue.attribute_value)
        .joinedload(AttributeValue.attribute)
    )


def create_product(
    db: Session,
    product: models.ProductCreate,
    image_paths: Optional[List[str]] = None,
    attribute_value_ids: Optional[List[int]] = None
) -> models.ProductWithCategory:
    try:
        db_product = Product(
            title=product.title,
            description=product.description,
            category_id=product.category_id,
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

        # Create the default PKR price row.
        # NOTE (future — multi-currency): Accept a list of {currency_code, amount}
        # pairs from the request and insert one ProductPrice per currency here.
        db.add(ProductPrice(
            product_id=db_product.id,
            currency_code=_DEFAULT_CURRENCY,
            amount=product.price_amount,
            is_active=True,
        ))

        if attribute_value_ids:
            for av_id in attribute_value_ids:
                pav = ProductAttributeValue(
                    product_id=db_product.id,
                    attribute_value_id=av_id
                )
                db.add(pav)

        db.commit()

        # Reload with all joins so _build_product_response can resolve price_amount.
        logger.info(f"Created new product: {product.title} with {len(image_paths or [])} images")
        return get_product_by_id(db, db_product.id)

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
        query = _product_query_base(db)

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

        # Price filtering via correlated subquery against product_prices.
        # NOTE (future — multi-currency): Pass the request's currency_code to
        # _active_price_subquery() and min_price/max_price will filter in that currency.
        if min_price is not None or max_price is not None:
            price_sq = _active_price_subquery(_DEFAULT_CURRENCY).correlate(Product).scalar_subquery()
            if min_price is not None:
                query = query.filter(price_sq >= min_price)
            if max_price is not None:
                query = query.filter(price_sq <= max_price)

        if in_stock is not None:
            query = query.filter(
                Product.stock_quantity > 0 if in_stock else Product.stock_quantity == 0
            )

        # Attribute filtering with AND semantics across different attributes
        if attribute_value_ids:
            value_to_attr = {}
            attr_values = db.query(AttributeValue).filter(
                AttributeValue.id.in_(attribute_value_ids)
            ).all()
            
            for av in attr_values:
                if av.attribute_id not in value_to_attr:
                    value_to_attr[av.attribute_id] = []
                value_to_attr[av.attribute_id].append(av.id)
            
            for attr_id, val_ids in value_to_attr.items():
                query = query.filter(
                    Product.id.in_(
                        db.query(ProductAttributeValue.product_id)
                        .filter(ProductAttributeValue.attribute_value_id.in_(val_ids))
                    )
                )

        # Sorting — price sorts use the correlated subquery.
        if sort_by in ("price-low", "price-high"):
            price_sq = _active_price_subquery(_DEFAULT_CURRENCY).correlate(Product).scalar_subquery()
            if sort_by == "price-low":
                query = query.order_by(price_sq.asc())
            else:
                query = query.order_by(price_sq.desc())
        elif sort_by == "newest":
            query = query.order_by(Product.created_at.desc())
        elif sort_by == "name":
            query = query.order_by(Product.title.asc())
        else:  # featured / default
            query = query.order_by(Product.created_at.desc())

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
    """Get a specific product by ID with category and flat attributes."""
    product = _product_query_base(db).filter(Product.id == product_id).first()

    if not product:
        logger.warning(f"Product {product_id} not found")
        raise HTTPException(status_code=404, detail="Product not found")

    logger.info(f"Retrieved product {product_id}")
    return _build_product_response(product)


def update_product(db: Session, product_id: UUID, update_data: dict) -> models.ProductWithCategory:
    try:
        product = _get_product_orm(db, product_id)

        # Handle price_amount separately — it lives in product_prices, not Product.
        price_amount = update_data.pop("price_amount", None)
        if price_amount is not None:
            now = datetime.now(timezone.utc)
            existing_price = (
                db.query(ProductPrice)
                .filter(
                    ProductPrice.product_id == product_id,
                    ProductPrice.currency_code == _DEFAULT_CURRENCY,
                    ProductPrice.is_active == True,  # noqa: E712
                    ProductPrice.valid_from == None,  # noqa: E711  (default price row)
                )
                .first()
            )
            if existing_price:
                # In-place update preserves the audit-free MVP behaviour.
                # NOTE (future — price history): Set existing_price.is_active=False,
                # then insert a new row to keep a full price change audit trail.
                existing_price.amount = price_amount
            else:
                db.add(ProductPrice(
                    product_id=product_id,
                    currency_code=_DEFAULT_CURRENCY,
                    amount=price_amount,
                    is_active=True,
                ))

        # Update remaining scalar fields on Product.
        for field, value in update_data.items():
            setattr(product, field, value)

        db.commit()

        # Reload with all joins so _build_product_response can resolve price_amount.
        logger.info(f"Updated product {product_id} with fields: {list(update_data.keys())}")
        return get_product_by_id(db, product_id)

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
