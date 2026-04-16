from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException
import logging

from src.models.attribute import Attribute, AttributeValue
from src.models.category_attribute import CategoryAttribute

logger = logging.getLogger(__name__)


def get_attributes_for_category(db: Session, category_id: int) -> list[dict]:
    """
    Returns filterable attributes and their values for a given category ID.
    For each attribute assigned to the category, returns only:
      - values scoped to that category (category_id matches)
      - values that are global (category_id is NULL)

    Args:
        db: SQLAlchemy database session
        category_id: The ID of the category to get attributes for

    Returns:
        A list of dicts, each containing:
            - name: The attribute name (str)
            - values: list of dicts with 'id' and 'value' keys

    Example:
        [
            {
                "name": "material",
                "values": [
                    {"id": 1, "value": "crocodile skin"},
                    {"id": 2, "value": "snake skin"},
                    {"id": 3, "value": "leather"}
                ]
            },
            {
                "name": "accents",
                "values": [
                    {"id": 7, "value": "gold"},   # global (category_id=NULL)
                    {"id": 8, "value": "silver"}  # global (category_id=NULL)
                ]
            }
        ]
    """
    results = (
        db.query(Attribute)
        .join(CategoryAttribute, CategoryAttribute.attribute_id == Attribute.id)
        .options(joinedload(Attribute.values))
        .filter(CategoryAttribute.category_id == category_id)
        .all()
    )

    return [
        {
            "name": attr.name,
            "values": [
                {"id": v.id, "value": v.value}
                for v in attr.values
                # Return values scoped to this category OR global values (category_id=NULL)
                if v.category_id == category_id or v.category_id is None
            ]
        }
        for attr in results
    ]


def create_attribute(db: Session, name: str) -> Attribute:
    """Create a new global attribute (dimension only, no values yet)"""
    try:
        existing = db.query(Attribute).filter(Attribute.name == name).first()
        if existing:
            raise HTTPException(status_code=400, detail="Attribute name already exists")

        attribute = Attribute(name=name)
        db.add(attribute)
        db.commit()
        db.refresh(attribute)

        logger.info(f"Created attribute: {name}")
        return attribute

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create attribute {name}. Error: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create attribute")


def create_attribute_value(
    db: Session,
    attribute_id: int,
    value: str,
    category_id: int | None = None
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
            AttributeValue.value == value
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Value already exists for this attribute and category")

        attr_value = AttributeValue(
            attribute_id=attribute_id,
            value=value,
            category_id=category_id
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


def assign_attributes_to_category(
    db: Session,
    category_id: int,
    attribute_ids: list[int]
) -> list[CategoryAttribute]:
    """
    Assign a list of attributes to a category (Layer 2 of admin flow).
    Replaces existing assignments — sends the full desired list each time.
    """
    try:
        # Remove existing assignments for this category
        db.query(CategoryAttribute).filter(
            CategoryAttribute.category_id == category_id
        ).delete()

        # Create new assignments
        new_assignments = [
            CategoryAttribute(category_id=category_id, attribute_id=attr_id)
            for attr_id in attribute_ids
        ]
        db.add_all(new_assignments)
        db.commit()

        logger.info(f"Assigned attributes {attribute_ids} to category {category_id}")
        return new_assignments

    except Exception as e:
        logger.error(f"Failed to assign attributes to category {category_id}. Error: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to assign attributes to category")
