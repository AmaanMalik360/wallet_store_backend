from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from src.routes.models import ApiResponse


class AttributeValueResponse(BaseModel):
    id: int
    value: str


class AttributeFilterResponse(BaseModel):
    name: str
    values: List[AttributeValueResponse]


class CategoryBase(BaseModel):
    name: str
    parent_id: Optional[int] = None


class CategoryCreate(BaseModel):
    name: str
    parent_id: Optional[int] = None


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[int] = None


class CategoryData(BaseModel):
    id: int
    name: str
    slug: str
    parent_id: Optional[int] = None
    children: List['CategoryData'] = []
    filterable_attributes: List[AttributeFilterResponse] = []

    class Config:
        from_attributes = True


# Specific response types
class CategoryResponse(ApiResponse[CategoryData]):
    pass


class CategoriesListResponse(ApiResponse[List[CategoryData]]):
    pass


# Update forward reference for recursive model
CategoryData.model_rebuild()
