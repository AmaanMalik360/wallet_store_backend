from seeders.base_seeder import BaseSeeder
from models.category import Category

class CategorySeeder(BaseSeeder):
    """Seed categories with hierarchy"""
    
    def seed(self):
        print("🌱 Seeding categories...")
        
        # Clear existing data
        self.clear()
        
        # Define categories structure
        categories_data = [
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
        
        # Create categories recursively
        for parent_data in categories_data:
            parent = Category.create(self.db, parent_data["name"])
            
            # Create children
            for child_name in parent_data["children"]:
                Category.create(self.db, child_name, parent.id)
        
        self.db.commit()
        print(f"✅ Categories seeded successfully!")
    
    def clear(self):
        """Clear existing categories"""
        self.db.query(Category).delete()
        self.db.commit()
        print("🗑️  Cleared existing categories")
    