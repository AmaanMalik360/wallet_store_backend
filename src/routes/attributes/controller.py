from fastapi import APIRouter, status, HTTPException
from typing import List

from src.models.db import DbSession
from . import models
from .service import (
    get_attributes,
    get_attribute_by_id,
    create_attribute,
    update_attribute,
    delete_attribute,
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


@router.patch("/{attribute_id}", response_model=models.AttributeResponseWrapper)
def update_attribute_endpoint(attribute_id: int, attribute: models.AttributeUpdate, db: DbSession):
    """Update an attribute's name"""
    attr = update_attribute(db, attribute_id, attribute.name)
    return models.AttributeResponseWrapper(
        success=True,
        message="Attribute updated successfully",
        data=models.AttributeResponse(id=attr.id, name=attr.name)
    )


@router.delete("/{attribute_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attribute_endpoint(attribute_id: int, db: DbSession):
    """Delete an attribute and all its values"""
    delete_attribute(db, attribute_id)
