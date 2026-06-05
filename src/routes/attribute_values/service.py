from sqlalchemy.orm import Session
from fastapi import HTTPException
import logging

from src.models.attribute import Attribute, AttributeValue

logger = logging.getLogger(__name__)


def create_attribute_value(
    db: Session,
    attribute_id: int,
    value: str,
    category_id: int | None = None,
) -> AttributeValue:
    """
    Add a value to an attribute.
    - category_id=None  → global value, visible for all categories using this attribute
    - category_id=X     → scoped value, visible only when fetching attributes for category X
    """
    try:
        attribute = db.query(Attribute).filter(Attribute.id == attribute_id).first()
        if not attribute:
            raise HTTPException(status_code=404, detail="Attribute not found")

        existing = db.query(AttributeValue).filter(
            AttributeValue.attribute_id == attribute_id,
            AttributeValue.category_id == category_id,
            AttributeValue.value == value,
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Value already exists for this attribute and category")

        attr_value = AttributeValue(
            attribute_id=attribute_id,
            value=value,
            category_id=category_id,
        )
        db.add(attr_value)
        db.commit()
        db.refresh(attr_value)

        logger.info(f"Created attribute value '{value}' for attribute {attribute_id}, category_id={category_id}")
        return attr_value

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create attribute value. Error: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create attribute value")


def update_attribute_value(
    db: Session,
    value_id: int,
    value: str | None = None,
    category_id: int | None = None,
) -> AttributeValue:
    """Update an existing attribute value's text and/or category scope."""
    try:
        attr_value = db.query(AttributeValue).filter(AttributeValue.id == value_id).first()
        if not attr_value:
            raise HTTPException(status_code=404, detail="Attribute value not found")

        if value is not None:
            attr_value.value = value
        if category_id is not None:
            attr_value.category_id = category_id

        db.commit()
        db.refresh(attr_value)

        logger.info(f"Updated attribute value {value_id}")
        return attr_value

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update attribute value {value_id}. Error: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update attribute value")


def delete_attribute_value(db: Session, value_id: int) -> None:
    """Delete an attribute value by ID."""
    try:
        attr_value = db.query(AttributeValue).filter(AttributeValue.id == value_id).first()
        if not attr_value:
            raise HTTPException(status_code=404, detail="Attribute value not found")

        db.delete(attr_value)
        db.commit()

        logger.info(f"Deleted attribute value {value_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete attribute value {value_id}. Error: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete attribute value")
