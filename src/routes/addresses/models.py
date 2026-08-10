from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID
from src.routes.models import ApiResponse


class AddressCreate(BaseModel):
    line1: str = Field(..., max_length=255)
    line2: Optional[str] = Field(None, max_length=255)
    city: str = Field(..., max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: str = Field(..., min_length=2, max_length=2, description="ISO 3166-1 alpha-2")
    label: Optional[str] = Field(None, max_length=50)
    is_default: bool = False


class AddressResponse(BaseModel):
    id: UUID
    user_id: UUID
    line1: str
    line2: Optional[str] = None
    city: str
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: str
    label: Optional[str] = None
    is_default: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AddressResponseWrapper(ApiResponse[AddressResponse]):
    pass


class AddressListResponseWrapper(ApiResponse[list[AddressResponse]]):
    pass
