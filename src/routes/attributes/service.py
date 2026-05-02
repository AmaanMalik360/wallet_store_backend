from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException
import logging
from collections import defaultdict

from src.models.attribute import Attribute, AttributeValue
from src.models.category import Category
from src.models.category_attribute import CategoryAttribute

logger = logging.getLogger(__name__)


def build_filterable_attributes_for_category_map(
    db: Session,
    categories_by_id: dict[int, dict],
) -> dict[int, list[dict]]:
    """
    Build a map of filterable attributes for a batch of categories using in-memory ancestry traversal.

    This function answers the question: "For each given category, which attributes and their
    allowed values should be shown as filters?" It accounts for inherited attributes — i.e.,
    attributes assigned to ancestor categories are also considered applicable to descendant
    categories, since a product in a child category implicitly belongs to all parent categories.

    Steps performed:
        1. Queries all `CategoryAttribute` rows for the given category IDs to find which
           attributes are directly assigned to each category.
        2. For each category, walks up the parent chain (using `categories_by_id` in-memory,
           avoiding extra DB queries) to build a full lineage list: [self, parent, grandparent, ...].
        3. Merges attribute IDs from all ancestors into an inherited set per category.
        4. Fetches the full `Attribute` objects (with their `values` eagerly loaded) for all
           collected attribute IDs in a single batched query.
        5. For each category, builds a list of attribute dicts. Each attribute's `values` list
           is filtered to include only values that are either global (category_id is None) or
           belong to a category within the current category's lineage (ancestor-scoped values).
        6. Deduplicates values by ID and sorts attributes by ID for stable ordering.

    Args:
        db (Session):
            An active SQLAlchemy database session used to query `CategoryAttribute` and
            `Attribute` (with its `AttributeValue` children).

        categories_by_id (dict[int, dict]):
            A flat dictionary mapping category IDs to their data dicts. Each dict must
            contain at minimum a `"parent_id"` key (int or None) so the function can
            walk up the ancestor chain.

            Example:
                {
                    1: {"id": 1, "name": "Electronics", "parent_id": None},
                    2: {"id": 2, "name": "Phones",      "parent_id": 1},
                    3: {"id": 3, "name": "Smartphones", "parent_id": 2},
                }

    Returns:
        dict[int, list[dict]]:
            A dictionary mapping each category ID to its list of applicable filter attributes.
            Each attribute entry is a dict with the shape:
                {
                    "id":     int,         # Attribute primary key
                    "name":   str,         # Attribute display name (e.g. "Color", "Brand")
                    "values": list[dict],  # Filtered & deduplicated attribute values
                }
            Each value entry inside "values" is:
                {
                    "id":    int,  # AttributeValue primary key
                    "value": str,  # Display value (e.g. "Red", "Samsung")
                }

            If `categories_by_id` is empty or no attributes are found, returns an empty dict
            or a dict with empty lists respectively.

            Example output:
                {
                    2: [
                        {"id": 10, "name": "Brand",  "values": [{"id": 1, "value": "Samsung"}, ...]},
                        {"id": 11, "name": "Color",  "values": [{"id": 5, "value": "Black"}, ...]},
                    ],
                    3: [
                        {"id": 10, "name": "Brand",  "values": [{"id": 1, "value": "Samsung"}, ...]},
                    ],
                }
    """
    category_ids = list(categories_by_id.keys())
    if not category_ids:
        return {}

    category_attribute_rows = (
        db.query(CategoryAttribute)
        .filter(CategoryAttribute.category_id.in_(category_ids))
        .all()
    )

    direct_attr_ids_by_category: dict[int, set[int]] = defaultdict(set)
    for row in category_attribute_rows:
        direct_attr_ids_by_category[row.category_id].add(row.attribute_id)

    lineage_by_category: dict[int, list[int]] = {}
    for category_id in category_ids:
        lineage: list[int] = []
        visited: set[int] = set()
        current_id = category_id

        while current_id is not None and current_id not in visited:
            lineage.append(current_id)
            visited.add(current_id)
            parent_id = categories_by_id[current_id]["parent_id"]
            current_id = parent_id if parent_id in categories_by_id else None

        lineage_by_category[category_id] = lineage

    inherited_attr_ids_by_category: dict[int, set[int]] = {}
    all_attribute_ids: set[int] = set()

    for category_id, lineage in lineage_by_category.items():
        attribute_ids: set[int] = set()
        for ancestor_id in lineage:
            attribute_ids.update(direct_attr_ids_by_category.get(ancestor_id, set()))
        inherited_attr_ids_by_category[category_id] = attribute_ids
        all_attribute_ids.update(attribute_ids)

    if not all_attribute_ids:
        return {category_id: [] for category_id in category_ids}

    attributes = (
        db.query(Attribute)
        .options(joinedload(Attribute.values))
        .filter(Attribute.id.in_(all_attribute_ids))
        .all()
    )
    attributes_by_id = {attr.id: attr for attr in attributes}

    result: dict[int, list[dict]] = {}

    for category_id, attribute_ids in inherited_attr_ids_by_category.items():
        lineage_set = set(lineage_by_category[category_id])
        category_attributes: list[dict] = []

        for attribute_id in sorted(attribute_ids):
            attr = attributes_by_id.get(attribute_id)
            if not attr:
                continue

            values: list[dict] = []
            seen_value_ids: set[int] = set()

            for value in attr.values:
                if value.id in seen_value_ids:
                    continue

                if value.category_id is None or value.category_id in lineage_set:
                    values.append({"id": value.id, "value": value.value})
                    seen_value_ids.add(value.id)

            category_attributes.append(
                {
                    "id": attr.id,
                    "name": attr.name,
                    "values": values,
                }
            )

        result[category_id] = category_attributes

    return result


def get_category_lineage_ids(db: Session, category_id: int) -> list[int]:
    """Return lineage category IDs from current category up to root."""
    current_category = db.query(Category).filter(Category.id == category_id).first()
    if not current_category:
        return []

    lineage_ids: list[int] = []
    visited_ids: set[int] = set()

    while current_category and current_category.id not in visited_ids:
        lineage_ids.append(current_category.id)
        visited_ids.add(current_category.id)

        if current_category.parent_id is None:
            break

        current_category = db.query(Category).filter(Category.id == current_category.parent_id).first()

    return lineage_ids


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
                "id": 1,
                "name": "material",
                "values": [
                    {"id": 1, "value": "crocodile skin"},
                    {"id": 2, "value": "snake skin"},
                    {"id": 3, "value": "leather"}
                ]
            },
            {
                "id": 2,
                "name": "accents",
                "values": [
                    {"id": 7, "value": "gold"},   # global (category_id=NULL)
                    {"id": 8, "value": "silver"}  # global (category_id=NULL)
                ]
            }
        ]
    """
    lineage_ids = get_category_lineage_ids(db, category_id)
    if not lineage_ids:
        return []

    results = (
        db.query(Attribute)
        .join(CategoryAttribute, CategoryAttribute.attribute_id == Attribute.id)
        .options(joinedload(Attribute.values))
        .filter(CategoryAttribute.category_id.in_(lineage_ids))
        .all()
    )
    logger.info(
        "Retrieved %s attributes for category %s with lineage %s",
        len(results),
        category_id,
        lineage_ids,
    )

    attributes_by_id: dict[int, Attribute] = {}
    for attr in results:
        if attr.id not in attributes_by_id:
            attributes_by_id[attr.id] = attr

    return [
        {
            "id": attr.id,
            "name": attr.name,
            "values": [
                {"id": v.id, "value": v.value}
                for v in attr.values
                # Return global values OR values scoped to category lineage
                if v.category_id is None or v.category_id in lineage_ids
            ]
        }
        for attr in attributes_by_id.values()
    ]


def get_attributes(db: Session) -> list[Attribute]:
    """Get all attributes"""
    try:
        attributes = db.query(Attribute).order_by(Attribute.name).all()
        logger.info(f"Retrieved {len(attributes)} attributes")
        return attributes
    except Exception as e:
        logger.error(f"Failed to retrieve attributes. Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve attributes")


def get_attribute_by_id(db: Session, attribute_id: int) -> Attribute:
    """Get a single attribute with its values"""
    attribute = (
        db.query(Attribute)
        .options(joinedload(Attribute.values))
        .filter(Attribute.id == attribute_id)
        .first()
    )
    if not attribute:
        raise HTTPException(status_code=404, detail="Attribute not found")
    logger.info(f"Retrieved attribute {attribute_id}")
    return attribute


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
