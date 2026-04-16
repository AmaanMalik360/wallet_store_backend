from fastapi import APIRouter, status, HTTPException
from typing import List

from src.models.db import DbSession
from . import models
from .service import (
    create_attribute,
    create_attribute_value
)

router = APIRouter(
    prefix="/attributes",
    tags=["Attributes"]
)


@router.post("/", response_model=models.AttributeResponseWrapper, status_code=status.HTTP_201_CREATED)
def create_attribute_endpoint(attribute: models.AttributeCreate, db: DbSession):
    """Create a new global attribute (dimension only, no values yet)"""
    attr = create_attribute(db, attribute.name)
    return models.AttributeResponseWrapper(
        success=True,
        message="Attribute created successfully",
        data=models.AttributeResponse(id=attr.id, name=attr.name)
    )


@router.post("/{attribute_id}/values", response_model=models.AttributeValueResponseWrapper, status_code=status.HTTP_201_CREATED)
def create_attribute_value_endpoint(
    attribute_id: int,
    attr_value: models.AttributeValueCreate,
    db: DbSession
):
    """
    Add a value to an attribute.
    - category_id=None  → global value, visible for all categories using this attribute
    - category_id=X     → scoped value, visible only when fetching attributes for category X
    """
    attr_val = create_attribute_value(db, attribute_id, attr_value.value, attr_value.category_id)
    return models.AttributeValueResponseWrapper(
        success=True,
        message="Attribute value created successfully",
        data=models.AttributeValueResponse(
            id=attr_val.id,
            attribute_id=attr_val.attribute_id,
            value=attr_val.value,
            category_id=attr_val.category_id
        )
    )
