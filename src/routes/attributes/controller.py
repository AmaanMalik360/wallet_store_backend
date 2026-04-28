from fastapi import APIRouter, status, HTTPException
from typing import List

from src.models.db import DbSession
from . import models
from .service import (
    get_attributes,
    get_attribute_by_id,
    create_attribute,
    create_attribute_value
)

router = APIRouter(
    prefix="/attributes",
    tags=["Attributes"]
)


@router.get("/", response_model=models.AttributeListResponseWrapper)
def list_attributes(db: DbSession):
    """Get all attributes"""
    attrs = get_attributes(db)
    return models.AttributeListResponseWrapper(
        success=True,
        message="Attributes retrieved successfully",
        data=[models.AttributeResponse(id=a.id, name=a.name) for a in attrs]
    )


@router.get("/{attribute_id}", response_model=models.AttributeWithValuesResponseWrapper)
def get_attribute(attribute_id: int, db: DbSession):
    """Get a single attribute with its values"""
    attr = get_attribute_by_id(db, attribute_id)
    return models.AttributeWithValuesResponseWrapper(
        success=True,
        message="Attribute retrieved successfully",
        data=models.AttributeWithValuesResponse(
            id=attr.id,
            name=attr.name,
            values=[
                models.AttributeValueResponse(
                    id=v.id,
                    attribute_id=v.attribute_id,
                    value=v.value,
                    category_id=v.category_id
                )
                for v in attr.values
            ]
        )
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
