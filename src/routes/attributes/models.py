from pydantic import BaseModel
from typing import Optional, List
from src.routes.models import ApiResponse
from src.routes.attribute_values.models import AttributeValueResponse


class AttributeCreate(BaseModel):
    name: str


class AttributeUpdate(BaseModel):
    name: str


class AssignAttributesRequest(BaseModel):
    attribute_ids: List[int]


class AttributeResponse(BaseModel):
    id: int
    name: str

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


class AttributeListResponseWrapper(ApiResponse[List[AttributeResponse]]):
    pass


class AttributeWithValuesResponseWrapper(ApiResponse[AttributeWithValuesResponse]):
    pass
