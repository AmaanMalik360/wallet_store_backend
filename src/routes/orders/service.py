from uuid import UUID
from typing import Optional
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException
import logging

from src.models.order import Order, OrderItem, OrderStatus
from src.models.product import Product
from src.models.shipment import Shipment
from src.models.user import User
from . import models

logger = logging.getLogger(__name__)

CUSTOMER_VISIBLE_STATUSES = [
    OrderStatus.PAID,
    OrderStatus.PROCESSING,
    OrderStatus.SHIPPED,
    OrderStatus.DELIVERED,
    OrderStatus.CANCELLED,
]


def _load_order(db: Session, order_id: UUID) -> Order:
    order = (
        db.query(Order)
        .options(
            joinedload(Order.items),
            joinedload(Order.shipping_address),
            joinedload(Order.billing_address),
            joinedload(Order.user),
            joinedload(Order.shipments),
        )
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


def _build_order_response(order: Order, db: Session) -> models.OrderResponse:
    items_out = []
    for item in order.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        image = None
        if product and product.images:
            image = product.images[0]
        items_out.append(
            models.OrderItemResponse(
                product_id=item.product_id,
                title=product.title if product else "Deleted product",
                price_cents=item.price_cents,
                quantity=item.quantity,
                image=image,
            )
        )
    return models.OrderResponse(
        id=order.id,
        user_id=order.user_id,
        total_cents=order.total_cents,
        status=order.status.value,
        source=order.source,
        notes=order.notes,
        shipping_address=order.shipping_address,
        billing_address=order.billing_address,
        items=items_out,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


def create_order(db: Session, user_id: UUID, data: models.OrderCreate) -> models.OrderResponse:
    try:
        total_cents = 0
        order_items = []
        for item_in in data.items:
            product = db.query(Product).filter(Product.id == item_in.product_id).first()
            if not product:
                raise HTTPException(status_code=404, detail=f"Product {item_in.product_id} not found")
            line_total = product.price * item_in.quantity
            total_cents += line_total
            order_items.append(
                OrderItem(
                    product_id=item_in.product_id,
                    quantity=item_in.quantity,
                    price_cents=product.price,
                )
            )

        order = Order(
            user_id=user_id,
            total_cents=total_cents,
            status=OrderStatus.PENDING_PAYMENT,
            source=data.source,
            shipping_address_id=data.shipping_address_id,
            billing_address_id=data.billing_address_id,
        )
        db.add(order)
        db.flush()

        for oi in order_items:
            oi.order_id = order.id
        db.add_all(order_items)
        db.commit()

        order = _load_order(db, order.id)
        logger.info(f"Created order {order.id} for user {user_id}")
        return _build_order_response(order, db)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create order. Error: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create order")


def get_my_orders(db: Session, user_id: UUID) -> list[models.OrderListItem]:
    orders = (
        db.query(Order)
        .options(joinedload(Order.items), joinedload(Order.user))
        .filter(Order.user_id == user_id, Order.status.in_(CUSTOMER_VISIBLE_STATUSES))
        .order_by(Order.created_at.desc())
        .all()
    )
    return [_to_list_item(o, db) for o in orders]


def get_my_order(db: Session, user_id: UUID, order_id: UUID) -> models.OrderResponse:
    order = _load_order(db, order_id)
    if order.user_id != user_id:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status not in CUSTOMER_VISIBLE_STATUSES:
        raise HTTPException(status_code=404, detail="Order not found")
    return _build_order_response(order, db)


def _to_list_item(order: Order, db: Session) -> models.OrderListItem:
    user = order.user
    first_item = order.items[0] if order.items else None
    first_title = None
    if first_item:
        p = db.query(Product).filter(Product.id == first_item.product_id).first()
        first_title = p.title if p else "Deleted product"
    return models.OrderListItem(
        id=order.id,
        user_id=order.user_id,
        total_cents=order.total_cents,
        status=order.status.value,
        source=order.source,
        customer_name=user.name if user else None,
        customer_email=user.email if user else None,
        item_count=len(order.items),
        first_item_title=first_title,
        created_at=order.created_at,
    )


def admin_list_orders(
    db: Session,
    status: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> models.PaginatedOrdersResponse:
    query = db.query(Order).options(joinedload(Order.items), joinedload(Order.user))

    if status:
        try:
            status_enum = OrderStatus(status)
            query = query.filter(Order.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    if search:
        query = query.join(Order.user).filter(
            (User.name.ilike(f"%{search}%")) | (User.email.ilike(f"%{search}%"))
        )

    total = query.count()
    orders = query.order_by(Order.created_at.desc()).offset(skip).limit(limit).all()

    return models.PaginatedOrdersResponse(
        data=[_to_list_item(o, db) for o in orders],
        total=total,
        skip=skip,
        limit=limit,
    )


def admin_get_order(db: Session, order_id: UUID) -> models.OrderResponse:
    order = _load_order(db, order_id)
    return _build_order_response(order, db)


def admin_update_status(db: Session, order_id: UUID, status: OrderStatus) -> models.OrderResponse:
    order = _load_order(db, order_id)
    order.status = status
    db.commit()
    order = _load_order(db, order_id)
    logger.info(f"Updated order {order_id} status to {status.value}")
    return _build_order_response(order, db)


def admin_replace_items(db: Session, order_id: UUID, data: models.ReplaceOrderItems) -> models.OrderResponse:
    try:
        order = _load_order(db, order_id)

        db.query(OrderItem).filter(OrderItem.order_id == order_id).delete()

        total_cents = 0
        new_items = []
        for item_in in data.items:
            product = db.query(Product).filter(Product.id == item_in.product_id).first()
            if not product:
                raise HTTPException(status_code=404, detail=f"Product {item_in.product_id} not found")
            total_cents += product.price * item_in.quantity
            new_items.append(
                OrderItem(
                    order_id=order_id,
                    product_id=item_in.product_id,
                    quantity=item_in.quantity,
                    price_cents=product.price,
                )
            )

        db.add_all(new_items)
        order.total_cents = total_cents
        db.commit()
        order = _load_order(db, order_id)
        logger.info(f"Replaced items on order {order_id}")
        return _build_order_response(order, db)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to replace items on order {order_id}. Error: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update order items")


def admin_update_meta(db: Session, order_id: UUID, data: models.UpdateOrderMeta) -> models.OrderResponse:
    order = _load_order(db, order_id)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(order, field, value)
    db.commit()
    order = _load_order(db, order_id)
    logger.info(f"Updated meta on order {order_id}")
    return _build_order_response(order, db)


def admin_upsert_shipment(db: Session, order_id: UUID, data: models.UpsertShipment) -> models.OrderResponse:
    try:
        _load_order(db, order_id)

        shipment = db.query(Shipment).filter(Shipment.order_id == order_id).first()
        if shipment:
            if data.carrier is not None:
                shipment.carrier = data.carrier
            if data.tracking_number is not None:
                shipment.tracking_number = data.tracking_number
            if data.shipped_at is not None:
                shipment.shipped_at = data.shipped_at
        else:
            shipment = Shipment(
                order_id=order_id,
                carrier=data.carrier,
                tracking_number=data.tracking_number,
                shipped_at=data.shipped_at,
            )
            db.add(shipment)

        db.commit()
        order = _load_order(db, order_id)
        logger.info(f"Upserted shipment on order {order_id}")
        return _build_order_response(order, db)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upsert shipment on order {order_id}. Error: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update shipment")


def admin_delete_order(db: Session, order_id: UUID) -> None:
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    db.delete(order)
    db.commit()
    logger.info(f"Deleted order {order_id}")
