from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class AttributeValueResponse(BaseModel):
    id: int
    value: str


class AttributeFilterResponse(BaseModel):
    name: str
    values: List[AttributeValueResponse]


class CategoryBase(BaseModel):
    name: str
    slug: str
    parent_id: Optional[int] = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[int] = None


class CategoryResponse(CategoryBase):
    id: int
    slug: str
    children: List['CategoryResponse'] = []
    filterable_attributes: List[AttributeFilterResponse] = []

    class Config:
        from_attributes = True


# Update forward reference for recursive model
CategoryResponse.model_rebuild()
