"""
Product seeder with ProductPrice rows.

Run order:
    1. category_seeder.py   (categories must exist for FK)
    2. currency_seeder.py   (PKR row must exist for FK in product_prices)
    3. this file            (products + product_prices)

All prices are in PAISA (minor units of PKR). 1 PKR = 100 paisa.
Example: PKR 2,500 → 250000 paisa.

NOTE (future — multi-currency pricing):
    For each product, add additional ProductPrice rows with the target
    currency_code and the converted amount. No schema changes are needed;
    just insert the extra rows here (or via an admin UI).
"""
from seeders.base_seeder import BaseSeeder
from src.models.product import Product
from src.models.product_price import ProductPrice
from src.models.category import Category


PRODUCTS_DATA = [
    # ── Bi-fold wallets ─────────────────────────────────────────────────────
    {
        "title": "Classic Leather Bifold Wallet",
        "description": "Genuine cowhide leather bifold wallet with 6 card slots and a bill compartment.",
        "category": "bi fold",
        "price_pkr": 250000,  # PKR 2,500 in paisa
        "stock_quantity": 25,
    },
    {
        "title": "Slim Bifold Wallet",
        "description": "Minimalist bifold wallet made from full-grain leather.",
        "category": "bi fold",
        "price_pkr": 199000,
        "stock_quantity": 40,
    },
    # ── Slim wallets ────────────────────────────────────────────────────────
    {
        "title": "Ultra Slim Card Holder Wallet",
        "description": "Holds up to 8 cards in a slim profile under 6mm.",
        "category": "slim wallets",
        "price_pkr": 149000,
        "stock_quantity": 60,
    },
    # ── RFID wallets ────────────────────────────────────────────────────────
    {
        "title": "RFID Blocking Leather Wallet",
        "description": "Protects your cards from RFID skimming with a faraday cage lining.",
        "category": "rfid wallets",
        "price_pkr": 320000,
        "stock_quantity": 30,
    },
    # ── Card holders ─────────────────────────────────────────────────────────
    {
        "title": "Aluminium Card Holder",
        "description": "Brushed aluminium card holder with spring-loaded ejector.",
        "category": "card holders",
        "price_pkr": 185000,
        "stock_quantity": 50,
    },
    # ── Keychains ────────────────────────────────────────────────────────────
    {
        "title": "Leather Keychain",
        "description": "Full-grain leather keychain with a stainless-steel ring.",
        "category": "keychains",
        "price_pkr": 75000,
        "stock_quantity": 100,
    },
]


class ProductSeeder(BaseSeeder):
    """Seed demo products and their default PKR prices."""

    def seed(self):
        print("Seeding products...")
        self.clear()

        for data in PRODUCTS_DATA:
            category = (
                self.db.query(Category)
                .filter(Category.name == data["category"])
                .first()
            )
            product = Product(
                title=data["title"],
                description=data["description"],
                category_id=category.id if category else None,
                stock_quantity=data["stock_quantity"],
            )
            self.db.add(product)
            self.db.flush()

            # Create the default PKR price row.
            # NOTE (future — multi-currency): Add more ProductPrice rows here with
            # different currency_code values when expanding beyond PKR.
            self.db.add(ProductPrice(
                product_id=product.id,
                currency_code="PKR",
                amount=data["price_pkr"],
                is_active=True,
            ))

        self.db.commit()
        print("Products seeded successfully!")

    def clear(self):
        """Clear products (product_prices cascade via ondelete=CASCADE)."""
        self.db.query(Product).delete()
        self.db.commit()
        print("Cleared existing products and their prices")
