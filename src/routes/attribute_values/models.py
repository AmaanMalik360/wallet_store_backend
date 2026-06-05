from pydantic import BaseModel
from typing import Optional
from src.routes.models import ApiResponse


class AttributeValueCreate(BaseModel):
    value: str
    category_id: Optional[int] = None


class AttributeValueUpdate(BaseModel):
    value: Optional[str] = None
    category_id: Optional[int] = None


class AttributeValueResponse(BaseModel):
    id: int
    attribute_id: int
    value: str
    category_id: Optional[int] = None

    class Config:
        from_attributes = True


class AttributeValueResponseWrapper(ApiResponse[AttributeValueResponse]):
    pass
