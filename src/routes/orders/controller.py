from fastapi import APIRouter, Depends, Query, status
from typing import Optional
from uuid import UUID

from src.models.db import DbSession
from src.auth.dependencies import CurrentUser, require_permission
from . import models, service

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("/", response_model=models.OrderResponseWrapper, status_code=status.HTTP_201_CREATED)
def create_order(body: models.OrderCreate, db: DbSession, current_user: CurrentUser):
    order = service.create_order(db, current_user.id, body)
    return models.OrderResponseWrapper(
        success=True,
        message="Order created successfully",
        data=order,
    )


@router.get("/mine", response_model=models.PaginatedOrdersResponseWrapper)
def get_my_orders(db: DbSession, current_user: CurrentUser):
    orders = service.get_my_orders(db, current_user.id)
    return models.PaginatedOrdersResponseWrapper(
        success=True,
        message="Orders retrieved successfully",
        data=models.PaginatedOrdersResponse(
            data=orders,
            total=len(orders),
            skip=0,
            limit=len(orders),
        ),
    )


@router.get("/mine/{order_id}", response_model=models.OrderResponseWrapper)
def get_my_order(order_id: UUID, db: DbSession, current_user: CurrentUser):
    order = service.get_my_order(db, current_user.id, order_id)
    return models.OrderResponseWrapper(
        success=True,
        message="Order retrieved successfully",
        data=order,
    )


@router.get(
    "/",
    response_model=models.PaginatedOrdersResponseWrapper,
    dependencies=[Depends(require_permission("admin:access"))],
)
def admin_list_orders(
    db: DbSession,
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    result = service.admin_list_orders(db, status=status, search=search, skip=skip, limit=limit)
    return models.PaginatedOrdersResponseWrapper(
        success=True,
        message="Orders retrieved successfully",
        data=result,
    )


@router.get(
    "/{order_id}",
    response_model=models.OrderResponseWrapper,
    dependencies=[Depends(require_permission("admin:access"))],
)
def admin_get_order(order_id: UUID, db: DbSession):
    order = service.admin_get_order(db, order_id)
    return models.OrderResponseWrapper(
        success=True,
        message="Order retrieved successfully",
        data=order,
    )


@router.patch(
    "/{order_id}/status",
    response_model=models.OrderResponseWrapper,
    dependencies=[Depends(require_permission("admin:access"))],
)
def admin_update_status(order_id: UUID, body: models.UpdateOrderStatus, db: DbSession):
    order = service.admin_update_status(db, order_id, body.status)
    return models.OrderResponseWrapper(
        success=True,
        message="Order status updated",
        data=order,
    )


@router.put(
    "/{order_id}/items",
    response_model=models.OrderResponseWrapper,
    dependencies=[Depends(require_permission("admin:access"))],
)
def admin_replace_items(order_id: UUID, body: models.ReplaceOrderItems, db: DbSession):
    order = service.admin_replace_items(db, order_id, body)
    return models.OrderResponseWrapper(
        success=True,
        message="Order items updated",
        data=order,
    )


@router.patch(
    "/{order_id}",
    response_model=models.OrderResponseWrapper,
    dependencies=[Depends(require_permission("admin:access"))],
)
def admin_update_meta(order_id: UUID, body: models.UpdateOrderMeta, db: DbSession):
    order = service.admin_update_meta(db, order_id, body)
    return models.OrderResponseWrapper(
        success=True,
        message="Order updated",
        data=order,
    )


@router.post(
    "/{order_id}/shipment",
    response_model=models.OrderResponseWrapper,
    dependencies=[Depends(require_permission("admin:access"))],
)
def admin_upsert_shipment(order_id: UUID, body: models.UpsertShipment, db: DbSession):
    order = service.admin_upsert_shipment(db, order_id, body)
    return models.OrderResponseWrapper(
        success=True,
        message="Shipment updated",
        data=order,
    )


@router.delete(
    "/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("admin:access"))],
)
def admin_delete_order(order_id: UUID, db: DbSession):
    service.admin_delete_order(db, order_id)
