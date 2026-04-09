# seeders/attribute_seeder.py
from seeders.base_seeder import BaseSeeder
from models.attribute import Attribute, AttributeValue

class AttributeSeeder(BaseSeeder):
    """Seed attributes and their values"""

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
            {
                "name": "accents",
                "values": [
                    "Beaded",
                    "Bow",
                    "Button",
                ]
            },
        ]

        for attr_data in attributes_data:
            attribute = Attribute(name=attr_data["name"])
            self.db.add(attribute)
            self.db.flush()

            for value in attr_data["values"]:
                self.db.add(AttributeValue(attribute_id=attribute.id, value=value))

        self.db.commit()
        print("✅ Attributes seeded successfully!")

    def clear(self):
        """Clear existing attribute values and attributes"""
        self.db.query(AttributeValue).delete()
        self.db.query(Attribute).delete()
        self.db.commit()
        print("🗑️  Cleared existing attributes")