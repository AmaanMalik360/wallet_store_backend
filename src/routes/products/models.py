from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from fastapi import UploadFile
from src.routes.models import ApiResponse


class ProductBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    category_id: Optional[int] = None
    stock_quantity: int = Field(..., ge=0, description="Number of items in stock")
    sku: Optional[str] = None
    images: Optional[List[str]] = Field(default_factory=list, description="List of image URLs")


class ProductCreate(ProductBase):
    # price_amount is in minor units of currency_code (paisa for PKR; 1 PKR = 100 paisa).
    # NOTE (future — multi-currency): Add currency_code: str = "PKR" here when
    # the storefront lets admins set a price per currency at creation time.
    price_amount: int = Field(..., gt=0, description="Price in minor units (paisa for PKR)")


class ProductUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    category_id: Optional[int] = None
    # price_amount is in minor units (paisa for PKR).
    price_amount: Optional[int] = Field(None, gt=0, description="Price in minor units (paisa for PKR)")
    stock_quantity: Optional[int] = Field(None, ge=0, description="Number of items in stock")
    sku: Optional[str] = None
    images: Optional[List[str]] = None
    new_images: Optional[List[UploadFile]] = Field(default_factory=list, description="New image files to upload")


class ProductAttribute(BaseModel):
    value_id: int
    attribute_id: int
    name: str
    value: str


class ProductResponse(ProductBase):
    id: UUID
    # price_amount is resolved from the active ProductPrice for the default currency.
    # NOTE (future — multi-currency): Accept a currency_code query param and pass it
    # through to resolve_price(). The response would also include currency_code.
    price_amount: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CategoryInProduct(BaseModel):
    id: int
    name: str
    slug: str
    parent_id: Optional[int] = None
    
    class Config:
        from_attributes = True


class ProductWithCategory(ProductResponse):
    category: Optional[CategoryInProduct] = None
    attributes: List[ProductAttribute] = []


class PaginatedProductsResponse(BaseModel):
    data: List[ProductWithCategory]
    total: int
    skip: int
    limit: int


# Response wrapper types using shared ApiResponse
class ProductResponseWrapper(ApiResponse[ProductResponse]):
    pass


class ProductWithCategoryResponseWrapper(ApiResponse[ProductWithCategory]):
    pass


class PaginatedProductsResponseWrapper(ApiResponse[PaginatedProductsResponse]):
    pass
