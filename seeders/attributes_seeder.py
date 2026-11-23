# seeders/attribute_seeder.py
from seeders.base_seeder import BaseSeeder
from src.models.attribute import Attribute, AttributeValue, ProductAttributeValue
from src.models.category import Category
from src.models.category_attribute import CategoryAttribute

# Categories that should expose "material" as a filterable attribute.
# Descendants inherit it via the lineage-based lookup in
# build_filterable_attributes_for_category_map().
FILTERABLE_CATEGORIES = ("wallets", "bags", "accessories")


class AttributeSeeder(BaseSeeder):
    """
    Seed attributes, their values, and category assignments.

    Run AFTER category_seeder.py (CategoryAttribute FKs into categories)
    and BEFORE product_seeder.py (products link AttributeValue rows).

    Strict order dependency per the EAV design: attribute → values →
    category assignment. Without the CategoryAttribute rows below, the
    attribute never appears in a category's filterable_attributes and the
    storefront filter UI won't render it.
    """

    def seed(self):
        print("🌱 Seeding attributes...")

        self.clear()

        attributes_data = [
            {
                "name": "material",
                "values": [
                    "Cowhide Leather",
                    "Crocodile Leather",
                    "Snake Leather",
                    "Nylon",
                    "Aluminum",
                    "Faux Leather",
                ]
            },
        ]

        for attr_data in attributes_data:
            attribute = Attribute(name=attr_data["name"])
            self.db.add(attribute)
            self.db.flush()

            for value in attr_data["values"]:
                self.db.add(AttributeValue(attribute_id=attribute.id, value=value))

        self.db.flush()

        # Assign "material" to the leather-goods categories so it becomes
        # filterable (and inheritable by their subcategories).
        material = self.db.query(Attribute).filter(Attribute.name == "material").first()
        for cat_name in FILTERABLE_CATEGORIES:
            category = self.db.query(Category).filter(Category.name == cat_name).first()
            if not category:
                print(f"  ⚠️  category '{cat_name}' not found — run category_seeder.py first")
                continue
            exists = (
                self.db.query(CategoryAttribute)
                .filter_by(category_id=category.id, attribute_id=material.id)
                .first()
            )
            if not exists:
                self.db.add(CategoryAttribute(category_id=category.id, attribute_id=material.id))

        self.db.commit()
        print("✅ Attributes seeded successfully!")

    def clear(self):
        """Clear existing attribute values and attributes"""
        # category_attributes rows are removed by the DB-level CASCADE on
        # category_attributes.attribute_id when attributes are deleted.
        # product_attribute_values has no cascade — it must be cleared first.
        self.db.query(ProductAttributeValue).delete()
        self.db.query(AttributeValue).delete()
        self.db.query(Attribute).delete()
        self.db.commit()
        print("🗑️  Cleared existing attributes")
