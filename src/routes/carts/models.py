from pydantic import BaseModel, field_validator
from typing import Optional, List
from uuid import UUID

from src.routes.models import ApiResponse


class CartItemResponse(BaseModel):
    product_id: UUID
    title: str
    # price_amount is in minor units of the default currency (paisa for PKR).
    # NOTE (future — multi-currency): Add currency_code: str = "PKR" here so
    # the frontend can call formatPrice(price_amount, currency_code) dynamically.
    price_amount: int
    image: str
    category_name: Optional[str] = None
    quantity: int

    class Config:
        from_attributes = True


class CartResponse(BaseModel):
    cart_id: UUID
    user_id: UUID
    items: List[CartItemResponse]

    class Config:
        from_attributes = True


class AddItemRequest(BaseModel):
    product_id: UUID
    quantity: int

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("quantity must be >= 1")
        return v


class UpdateItemRequest(BaseModel):
    quantity: int

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("quantity must be >= 1")
        return v


class SyncCartRequest(BaseModel):
    items: List[AddItemRequest]


class CartResponseWrapper(ApiResponse[CartResponse]):
    pass
