from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID

from src.models.order import OrderStatus
from src.routes.models import ApiResponse
from src.routes.addresses.models import AddressResponse


class OrderItemCreate(BaseModel):
    product_id: UUID
    quantity: int = Field(..., ge=1)


class OrderCreate(BaseModel):
    items: list[OrderItemCreate] = Field(..., min_length=1)
    source: str = "whatsapp"
    shipping_address_id: Optional[UUID] = None
    billing_address_id: Optional[UUID] = None


class OrderItemResponse(BaseModel):
    product_id: UUID
    title: str
    price_cents: int
    quantity: int
    image: Optional[str] = None

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    id: UUID
    user_id: UUID
    total_cents: int
    status: str
    source: Optional[str] = None
    notes: Optional[str] = None
    shipping_address: Optional[AddressResponse] = None
    billing_address: Optional[AddressResponse] = None
    items: list[OrderItemResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrderListItem(BaseModel):
    id: UUID
    user_id: UUID
    total_cents: int
    status: str
    source: Optional[str] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    item_count: int
    first_item_title: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PaginatedOrdersResponse(BaseModel):
    data: list[OrderListItem]
    total: int
    skip: int
    limit: int


class UpdateOrderStatus(BaseModel):
    status: OrderStatus


class ReplaceOrderItems(BaseModel):
    items: list[OrderItemCreate] = Field(..., min_length=1)


class UpdateOrderMeta(BaseModel):
    shipping_address_id: Optional[UUID] = None
    billing_address_id: Optional[UUID] = None
    notes: Optional[str] = None


class UpsertShipment(BaseModel):
    carrier: Optional[str] = Field(None, max_length=50)
    tracking_number: Optional[str] = Field(None, max_length=100)
    shipped_at: Optional[datetime] = None


class OrderResponseWrapper(ApiResponse[OrderResponse]):
    pass


class PaginatedOrdersResponseWrapper(ApiResponse[PaginatedOrdersResponse]):
    pass
