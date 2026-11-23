"""
Product seeder with ProductPrice and ProductAttributeValue rows.

Run order:
    1. category_seeder.py    (categories must exist for FK + SKU prefix)
    2. currency_seeder.py    (PKR row must exist for FK in product_prices)
    3. attributes_seeder.py  (material AttributeValue rows must exist for links)
    4. this file             (products + product_prices + product_attribute_values)

All prices are in PAISA (minor units of PKR). 1 PKR = 100 paisa.
Example: PKR 2,500 → 250000 paisa.

Seeded prices deliberately span the storefront filter brackets
(< Rs 10,000 / 10–20k / 20–30k / > Rs 30,000) so every price filter
returns results in dev.

NOTE (future — multi-currency pricing):
    For each product, add additional ProductPrice rows with the target
    currency_code and the converted amount. No schema changes are needed;
    just insert the extra rows here (or via an admin UI).
"""
from seeders.base_seeder import BaseSeeder
from src.models.product import Product
from src.models.product_price import ProductPrice
from src.models.category import Category
from src.models.attribute import Attribute, AttributeValue, ProductAttributeValue
from src.routes.products.sku_generator import generate_sku


PRODUCTS_DATA = [
    # ── Bi-fold wallets ─────────────────────────────────────────────────────
    {
        "title": "Crocodile Bifold Wallet",
        "description": "Crocodile leather bifold wallet with 6 card slots and a bill compartment.",
        "category": "bi fold",
        "material": "Crocodile Leather",
        "price_pkr": 1850000,  # PKR 18,500 — Rs 10–20k bracket
        "stock_quantity": 12,
    },
    # ── Slim wallets ────────────────────────────────────────────────────────
    {
        "title": "Slim Snake Wallet",
        "description": "Minimalist snake leather wallet with a slim profile under 6mm.",
        "category": "slim wallets",
        "material": "Snake Leather",
        "price_pkr": 1650000,  # PKR 16,500 — Rs 10–20k bracket
        "stock_quantity": 20,
    },
    # ── RFID wallets ────────────────────────────────────────────────────────
    {
        "title": "RFID Blocking Bifold Wallet",
        "description": "Cowhide leather bifold with a faraday cage lining that protects cards from RFID skimming.",
        "category": "rfid wallets",
        "material": "Cowhide Leather",
        "price_pkr": 850000,  # PKR 8,500 — Under Rs 10k bracket
        "stock_quantity": 30,
    },
    # ── Long wallets ────────────────────────────────────────────────────────
    {
        "title": "Snake Long Wallet",
        "description": "Full-length snake leather wallet with zip pocket and ten card slots.",
        "category": "long wallets",
        "material": "Snake Leather",
        "price_pkr": 2200000,  # PKR 22,000 — Rs 20–30k bracket
        "stock_quantity": 10,
    },
    # ── Card holders ────────────────────────────────────────────────────────
    {
        "title": "Emerald Card Holder",
        "description": "Compact crocodile leather card holder with four slots and a center pocket.",
        "category": "card holders",
        "material": "Crocodile Leather",
        "price_pkr": 950000,  # PKR 9,500 — Under Rs 10k bracket
        "stock_quantity": 25,
    },
    # ── Keychains ────────────────────────────────────────────────────────────
    {
        "title": "Leather Keychain",
        "description": "Full-grain cowhide leather keychain with a stainless-steel ring.",
        "category": "keychains",
        "material": "Cowhide Leather",
        "price_pkr": 250000,  # PKR 2,500 — Under Rs 10k bracket
        "stock_quantity": 100,
    },
    # ── Travel bags ─────────────────────────────────────────────────────────
    {
        "title": "Snake Leather Travel Bag",
        "description": "Structured snake leather travel bag with reinforced handles and suede lining.",
        "category": "travel",
        "material": "Snake Leather",
        "price_pkr": 2900000,  # PKR 29,000 — Rs 20–30k bracket
        "stock_quantity": 8,
    },
    {
        "title": "Crocodile Travel Bag",
        "description": "Statement crocodile leather travel bag with brass hardware and shoulder strap.",
        "category": "travel",
        "material": "Crocodile Leather",
        "price_pkr": 3400000,  # PKR 34,000 — Over Rs 30k bracket
        "stock_quantity": 5,
    },
]


class ProductSeeder(BaseSeeder):
    """Seed demo products with PKR prices and material attribute links."""

    def _get_material_value(self, material_name: str) -> AttributeValue:
        return (
            self.db.query(AttributeValue)
            .join(Attribute, AttributeValue.attribute_id == Attribute.id)
            .filter(Attribute.name == "material", AttributeValue.value == material_name)
            .first()
        )

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

            # Auto-generate SKU — mirrors create_product() in the products service.
            product.sku = generate_sku(self.db, category)

            # Create the default PKR price row.
            # NOTE (future — multi-currency): Add more ProductPrice rows here with
            # different currency_code values when expanding beyond PKR.
            self.db.add(ProductPrice(
                product_id=product.id,
                currency_code="PKR",
                amount=data["price_pkr"],
                is_active=True,
            ))

            # Link the material attribute value so attribute filters include
            # this product. Requires attributes_seeder to have run first.
            material_value = self._get_material_value(data["material"])
            if material_value:
                self.db.add(ProductAttributeValue(
                    product_id=product.id,
                    attribute_value_id=material_value.id,
                ))
            else:
                print(f"  ⚠️  material '{data['material']}' not found for '{data['title']}' — run attributes_seeder.py first")

        self.db.commit()
        print("Products seeded successfully!")

    def clear(self):
        """Clear products (product_prices and product_attribute_values cascade
        via their ondelete=CASCADE FKs).

        NOTE: cart_items.product_id and order_items.product_id have NO cascade.
        If any cart or order references a seeded product, this bulk delete will
        raise an FK violation — clear those rows first.
        """
        self.db.query(Product).delete()
        self.db.commit()
        print("Cleared existing products and their prices")
