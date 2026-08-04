from fastapi import APIRouter, status
from uuid import UUID

from src.models.db import DbSession
from src.auth.dependencies import CurrentUser
from . import models
from . import service

router = APIRouter(prefix="/cart", tags=["Cart"])


@router.get("", response_model=models.CartResponseWrapper)
def get_cart(current_user: CurrentUser, db: DbSession):
    cart = service.get_cart_with_items(db, current_user.id)
    return models.CartResponseWrapper(
        success=True,
        message="Cart retrieved successfully",
        data=cart,
    )


@router.post("/items", response_model=models.CartResponseWrapper, status_code=status.HTTP_200_OK)
def add_cart_item(
    body: models.AddItemRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    cart = service.add_or_update_item(db, current_user.id, body.product_id, body.quantity)
    return models.CartResponseWrapper(
        success=True,
        message="Item added to cart",
        data=cart,
    )


@router.patch("/items/{product_id}", response_model=models.CartResponseWrapper)
def update_cart_item(
    product_id: UUID,
    body: models.UpdateItemRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    cart = service.update_item_quantity(db, current_user.id, product_id, body.quantity)
    return models.CartResponseWrapper(
        success=True,
        message="Cart item updated",
        data=cart,
    )


@router.delete("/items/{product_id}", response_model=models.CartResponseWrapper)
def remove_cart_item(
    product_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    cart = service.remove_item(db, current_user.id, product_id)
    return models.CartResponseWrapper(
        success=True,
        message="Item removed from cart",
        data=cart,
    )


@router.delete("", response_model=models.CartResponseWrapper)
def clear_cart(current_user: CurrentUser, db: DbSession):
    cart = service.clear_cart(db, current_user.id)
    return models.CartResponseWrapper(
        success=True,
        message="Cart cleared",
        data=cart,
    )


@router.post("/sync", response_model=models.CartResponseWrapper)
def sync_cart(
    body: models.SyncCartRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    cart = service.sync_cart(db, current_user.id, body.items)
    return models.CartResponseWrapper(
        success=True,
        message="Cart synced successfully",
        data=cart,
    )


@router.post("/replace", response_model=models.CartResponseWrapper)
def replace_cart(
    body: models.SyncCartRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    cart = service.replace_cart(db, current_user.id, body.items)
    return models.CartResponseWrapper(
        success=True,
        message="Cart replaced successfully",
        data=cart,
    )
