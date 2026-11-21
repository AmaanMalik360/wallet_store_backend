from seeders.base_seeder import BaseSeeder
from src.models.category import Category

class CategorySeeder(BaseSeeder):
    """Seed categories with hierarchy"""
    
    def seed(self):
        print("🌱 Seeding categories...")
        
        # Clear existing data
        self.clear()
        
        # Define categories structure
        categories_data = [
            {
                "name": "fashion",
                "children": [
                    {
                        "name": "wallets",
                        "children": [
                            "bi fold",
                            "slim wallets",
                            "rfid wallets",
                            "long wallets",
                            "card holders"
                        ]
                    },
                    {
                        "name": "bags",
                        "children": [
                            "travel"
                        ]
                    },
                    {
                        "name": "jackets",
                        "children": []  # No subcategories
                    },
                    {
                        "name": "accessories",
                        "children": [
                            "keychains"
                        ]
                    }
                ]
            }
        ]
        
        # Create categories recursively
        for category_data in categories_data:
            self._create_category(category_data)
        
        self.db.commit()
        print(f"✅ Categories seeded successfully!")
    
    def _create_category(self, category_data: dict, parent_id: int = None):
        """Recursively create a category and its children"""
        category = Category.create(self.db, category_data["name"], parent_id)
        
        for child in category_data.get("children", []):
            if isinstance(child, dict):
                self._create_category(child, category.id)
            else:
                Category.create(self.db, child, category.id)
    
    def clear(self):
        """Clear existing categories"""
        self.db.query(Category).delete()
        self.db.commit()
        print("🗑️  Cleared existing categories")
    