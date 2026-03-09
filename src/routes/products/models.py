from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class ProductBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    category_id: Optional[int] = None
    price: int = Field(..., gt=0, description="Price in cents")
    stock_quantity: int = Field(..., ge=0, description="Number of items in stock")
    images: Optional[List[str]] = Field(default_factory=list, description="List of image URLs")


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    category_id: Optional[int] = None
    price: Optional[int] = Field(None, gt=0, description="Price in cents")
    stock_quantity: Optional[int] = Field(None, ge=0, description="Number of items in stock")
    images: Optional[List[str]] = None


class ProductResponse(ProductBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ProductWithCategory(ProductResponse):
    category: Optional[dict] = None
    
    class Config:
        from_attributes = True
