from pydantic import BaseModel
from typing import Optional, List
from src.routes.models import ApiResponse


class AttributeCreate(BaseModel):
    name: str


class AttributeValueCreate(BaseModel):
    value: str
    category_id: Optional[int] = None


class AssignAttributesRequest(BaseModel):
    attribute_ids: List[int]


class AttributeResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class AttributeValueResponse(BaseModel):
    id: int
    attribute_id: int
    value: str
    category_id: Optional[int] = None

    class Config:
        from_attributes = True


class AttributeWithValuesResponse(BaseModel):
    id: int
    name: str
    values: List[AttributeValueResponse]

    class Config:
        from_attributes = True


# Response wrapper types using shared ApiResponse
class AttributeResponseWrapper(ApiResponse[AttributeResponse]):
    pass


class AttributeValueResponseWrapper(ApiResponse[AttributeValueResponse]):
    pass


class AttributeListResponseWrapper(ApiResponse[List[AttributeResponse]]):
    pass


class AttributeWithValuesResponseWrapper(ApiResponse[AttributeWithValuesResponse]):
    pass
