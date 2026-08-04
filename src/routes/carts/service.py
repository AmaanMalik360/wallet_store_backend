from typing import List
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException
import logging

from . import models
from src.models.cart import Cart, CartItem
from src.models.product import Product

logger = logging.getLogger(__name__)


def get_or_create_cart(db: Session, user_id: UUID) -> Cart:
    cart = db.query(Cart).filter(Cart.user_id == user_id).first()
    if not cart:
        cart = Cart(user_id=user_id)
        db.add(cart)
        db.flush()
    return cart


def _load_cart(db: Session, user_id: UUID) -> Cart:
    return (
        db.query(Cart)
        .options(
            joinedload(Cart.items)
            .joinedload(CartItem.product)
            .joinedload(Product.category)
        )
        .filter(Cart.user_id == user_id)
        .first()
    )


def _build_cart_response(cart: Cart) -> models.CartResponse:
    items = []
    for item in cart.items:
        product = item.product
        image = product.images[0] if product.images else ""
        category_name = product.category.name if product.category else None
        items.append(
            models.CartItemResponse(
                product_id=product.id,
                title=product.title,
                price=product.price,
                image=image,
                category_name=category_name,
                quantity=item.quantity,
            )
        )
    return models.CartResponse(
        cart_id=cart.id,
        user_id=cart.user_id,
        items=items,
    )


def get_cart_with_items(db: Session, user_id: UUID) -> models.CartResponse:
    try:
        cart = _load_cart(db, user_id)
        if not cart:
            get_or_create_cart(db, user_id)
            db.commit()
            cart = _load_cart(db, user_id)
        return _build_cart_response(cart)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get cart for user {user_id}. Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve cart")


def add_or_update_item(
    db: Session, user_id: UUID, product_id: UUID, quantity: int
) -> models.CartResponse:
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        cart = get_or_create_cart(db, user_id)

        existing_item = (
            db.query(CartItem)
            .filter(CartItem.cart_id == cart.id, CartItem.product_id == product_id)
            .first()
        )
        new_quantity = (existing_item.quantity + quantity) if existing_item else quantity

        if product.stock_quantity < new_quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock. Available: {product.stock_quantity}",
            )

        if existing_item:
            existing_item.quantity = new_quantity
        else:
            db.add(CartItem(cart_id=cart.id, product_id=product_id, quantity=quantity))

        db.commit()
        return get_cart_with_items(db, user_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add/update item {product_id} in cart. Error: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update cart")


def update_item_quantity(
    db: Session, user_id: UUID, product_id: UUID, quantity: int
) -> models.CartResponse:
    try:
        cart = db.query(Cart).filter(Cart.user_id == user_id).first()
        if not cart:
            raise HTTPException(status_code=404, detail="Cart not found")

        item = (
            db.query(CartItem)
            .filter(CartItem.cart_id == cart.id, CartItem.product_id == product_id)
            .first()
        )
        if not item:
            raise HTTPException(status_code=404, detail="Item not found in cart")

        if quantity <= 0:
            db.delete(item)
        else:
            item.quantity = quantity

        db.commit()
        return get_cart_with_items(db, user_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update quantity for item {product_id}. Error: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update item quantity")


def remove_item(
    db: Session, user_id: UUID, product_id: UUID
) -> models.CartResponse:
    try:
        cart = db.query(Cart).filter(Cart.user_id == user_id).first()
        if not cart:
            raise HTTPException(status_code=404, detail="Cart not found")

        item = (
            db.query(CartItem)
            .filter(CartItem.cart_id == cart.id, CartItem.product_id == product_id)
            .first()
        )
        if not item:
            raise HTTPException(status_code=404, detail="Item not found in cart")

        db.delete(item)
        db.commit()
        return get_cart_with_items(db, user_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove item {product_id} from cart. Error: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to remove item from cart")


def clear_cart(db: Session, user_id: UUID) -> models.CartResponse:
    try:
        cart = db.query(Cart).filter(Cart.user_id == user_id).first()
        if not cart:
            raise HTTPException(status_code=404, detail="Cart not found")

        db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
        db.commit()
        return get_cart_with_items(db, user_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to clear cart for user {user_id}. Error: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to clear cart")


def sync_cart(
    db: Session, user_id: UUID, items: List[models.AddItemRequest]
) -> models.CartResponse:
    try:
        cart = get_or_create_cart(db, user_id)

        for req_item in items:
            existing = (
                db.query(CartItem)
                .filter(
                    CartItem.cart_id == cart.id,
                    CartItem.product_id == req_item.product_id,
                )
                .first()
            )
            if existing:
                existing.quantity = max(existing.quantity, req_item.quantity)
            else:
                db.add(
                    CartItem(
                        cart_id=cart.id,
                        product_id=req_item.product_id,
                        quantity=req_item.quantity,
                    )
                )

        db.commit()
        return get_cart_with_items(db, user_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to sync cart for user {user_id}. Error: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to sync cart")


def replace_cart(
    db: Session, user_id: UUID, items: List[models.AddItemRequest]
) -> models.CartResponse:
    try:
        cart = get_or_create_cart(db, user_id)

        db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()

        for req_item in items:
            db.add(
                CartItem(
                    cart_id=cart.id,
                    product_id=req_item.product_id,
                    quantity=req_item.quantity,
                )
            )

        db.commit()
        return get_cart_with_items(db, user_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to replace cart for user {user_id}. Error: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to replace cart")
