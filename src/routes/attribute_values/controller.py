from fastapi import APIRouter, status

from src.models.db import DbSession
from . import models
from .service import (
    create_attribute_value,
    update_attribute_value,
    delete_attribute_value,
)

router = APIRouter(
    prefix="/attribute-values",
    tags=["Attribute Values"],
)


@router.post(
    "/{attribute_id}",
    response_model=models.AttributeValueResponseWrapper,
    status_code=status.HTTP_201_CREATED,
)
def create_attribute_value_endpoint(
    attribute_id: int,
    attr_value: models.AttributeValueCreate,
    db: DbSession,
):
    """
    Add a value to an attribute.
    - category_id=None  → global value, visible for all categories using this attribute
    - category_id=X     → scoped value, visible only when fetching attributes for category X
    """
    result = create_attribute_value(db, attribute_id, attr_value.value, attr_value.category_id)
    return models.AttributeValueResponseWrapper(
        success=True,
        message="Attribute value created successfully",
        data=models.AttributeValueResponse(
            id=result.id,
            attribute_id=result.attribute_id,
            value=result.value,
            category_id=result.category_id,
        ),
    )


@router.patch(
    "/{value_id}",
    response_model=models.AttributeValueResponseWrapper,
)
def update_attribute_value_endpoint(
    value_id: int,
    attr_value: models.AttributeValueUpdate,
    db: DbSession,
):
    """Update an existing attribute value's text and/or category scope."""
    result = update_attribute_value(db, value_id, attr_value.value, attr_value.category_id)
    return models.AttributeValueResponseWrapper(
        success=True,
        message="Attribute value updated successfully",
        data=models.AttributeValueResponse(
            id=result.id,
            attribute_id=result.attribute_id,
            value=result.value,
            category_id=result.category_id,
        ),
    )


@router.delete(
    "/{value_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_attribute_value_endpoint(value_id: int, db: DbSession):
    """Delete an attribute value by ID."""
    delete_attribute_value(db, value_id)
