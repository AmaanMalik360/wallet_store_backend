from sqlalchemy.orm import Session, joinedload
from src.models.attribute import Attribute, AttributeValue

CATEGORY_ATTRIBUTE_MAP: dict[str, list[str]] = {
    "wallets": ["material", "accents"],
    "bags": ["material", "accents"],
}

def get_attributes_for_category(db: Session, root_slug: str) -> list[dict]:
    """
    Returns filterable attributes and their values for a given root category slug.
    Falls back to empty list if category has no configured attributes.
    """
    attribute_names = CATEGORY_ATTRIBUTE_MAP.get(root_slug, [])
    if not attribute_names:
        return []

    attributes = (
        db.query(Attribute)
        .options(joinedload(Attribute.values))
        .filter(Attribute.name.in_(attribute_names))
        .all()
    )

    return [
        {
            "name": attr.name,
            "values": [
                {"id": v.id, "value": v.value}
                for v in attr.values
            ]
        }
        for attr in attributes
    ]
