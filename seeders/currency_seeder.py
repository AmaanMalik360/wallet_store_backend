from seeders.base_seeder import BaseSeeder
from src.models.currency import Currency


class CurrencySeeder(BaseSeeder):
    """
    Seeds the supported currencies.

    Run AFTER Migration 1 (currencies table), BEFORE ProductSeeder
    (ProductSeeder creates ProductPrice rows that FK into this table).

    To add a new currency in future (e.g. USD):
        self.db.add(Currency(code="USD", decimal_places=2, is_default=False))
    Re-run this seeder; the guard below prevents duplicate inserts.
    """

    def seed(self):
        print("Seeding currencies...")
        currencies = [
            Currency(code="PKR", decimal_places=2, is_default=True),
            # NOTE (future): add Currency(code="USD", decimal_places=2, is_default=False) here
            # when expanding to multi-currency. Also update CurrencyField.tsx and currency.ts.
        ]
        for currency in currencies:
            if not self.db.query(Currency).filter_by(code=currency.code).first():
                self.db.add(currency)
        self.db.commit()
        print("Currencies seeded successfully!")

    def clear(self):
        self.db.query(Currency).delete()
        self.db.commit()
        print("Cleared existing currencies")
