## Final Implementation Plan

I'll organize this into four layers: **Schema → Backend → Frontend → Deferred**.

---

## Layer 1 — Schema (Migrations)

Three migrations, in order. Fresh DB means no data to preserve, so these are straightforward.

### Migration 1 — Add `currencies` table

```python
# currencies
code           CHAR(3)    PRIMARY KEY         # "PKR"
decimal_places SMALLINT   NOT NULL DEFAULT 2
is_default     BOOLEAN    NOT NULL DEFAULT FALSE
```

No inline seed in the migration SQL. The `CurrencySeeder` runs after this migration
(see Execution Order). Keeping data out of migration files avoids re-seeding issues
on rollback/replay.

### Migration 2 — Create `product_prices`, drop `products.price`

```python
# product_prices
id            UUID        PRIMARY KEY         # generated Python-side via uuid6.uuid7 — NO server_default
product_id    UUID        FK → products.id  NOT NULL
currency_code CHAR(3)     FK → currencies.code  NOT NULL DEFAULT 'PKR'
amount        INTEGER     NOT NULL            # minor units (paisa)
is_active     BOOLEAN     NOT NULL DEFAULT TRUE
valid_from    TIMESTAMPTZ NULLABLE            # NULL = active from the moment of creation
valid_until   TIMESTAMPTZ NULLABLE            # NULL = no expiry (regular/permanent price)
```

**Do NOT use `UNIQUE (product_id, currency_code, valid_from)`.**
PostgreSQL does not consider `NULL = NULL` in unique constraints, so multiple rows with
`valid_from IS NULL` for the same product/currency would silently pass — exactly the
duplicate we need to prevent.

Use a **partial unique index** instead, created inside the migration:

```sql
CREATE UNIQUE INDEX uq_product_price_default
    ON product_prices (product_id, currency_code)
    WHERE valid_from IS NULL AND is_active = TRUE;
```

This enforces "only one active default price per product/currency" without the NULL problem.
Scheduled/future prices (`valid_from IS NOT NULL`) are not covered by this index and can
coexist as many rows as needed.

Then drop `products.price`.

### Migration 3 — Fix monetary column names on `orders`, `order_items`, and `payments`

```python
# orders
total_cents   → total_amount     # rename
# add:
currency_code   CHAR(3)  FK → currencies.code  NOT NULL DEFAULT 'PKR'

# order_items
price_cents   → unit_amount      # rename
# NO currency_code here — it always matches orders.currency_code (inherited, not duplicated)

# payments
amount_cents  → amount           # rename
# add:
currency_code   CHAR(3)  FK → currencies.code  NOT NULL DEFAULT 'PKR'
# Stripe/Razorpay require currency on the payment intent — this column must exist before
# any payment gateway integration.
```

---

## Layer 2 — Backend

Changes cascade from the schema changes. I'll list by file type.

### SQLAlchemy Models

**`Product` model** — remove `price` column entirely. Add `product_prices` relationship:

```python
product_prices: Mapped[list["ProductPrice"]] = relationship(
    "ProductPrice",
    back_populates="product",
    cascade="all, delete-orphan"
)
```

**New `Currency` model** (`src/models/currency.py`):

```python
class Currency(Base):
    __tablename__ = "currencies"
    code: Mapped[str] = mapped_column(CHAR(3), primary_key=True)
    decimal_places: Mapped[int] = mapped_column(SmallInteger, default=2)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
```

**New `ProductPrice` model** (`src/models/product_price.py`):

```python
from uuid6 import uuid7   # same import used by all other models in this codebase

class ProductPrice(Base):
    __tablename__ = "product_prices"
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    product_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    currency_code: Mapped[str] = mapped_column(CHAR(3), ForeignKey("currencies.code"), nullable=False, default="PKR")
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    valid_from: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    product: Mapped["Product"] = relationship("Product", back_populates="product_prices")
```

Note: `default=uuid7` is Python-side only (no `server_default`). SQLAlchemy calls `uuid7()`
in Python before the INSERT, then sends the value to PostgreSQL. PostgreSQL stores it as a
plain UUID — it does not need a native `uuid7()` function.

**`Order` model** — rename `total_cents` → `total_amount`, add `currency_code: Mapped[str]`.

**`OrderItem` model** — rename `price_cents` → `unit_amount`.

**`Payment` model** — rename `amount_cents` → `amount`, add `currency_code: Mapped[str]`.

### Pydantic Schemas

Every schema that referenced `price`, `total_cents`, or `price_cents` needs updating:

| Schema | Old field | New field |
|---|---|---|
| `ProductResponse` | `price: int` | `price_amount: int` (resolved server-side for the active PKR price) |
| `ProductCreate` / `ProductUpdate` | `price: int` | `price_amount: int` |
| `OrderResponse` | `total_cents: int` | `total_amount: int` + `currency_code: str` |
| `OrderItemResponse` | `price_cents: int` | `unit_amount: int` |
| `PaymentResponse` | `amount_cents: int` | `amount: int` + `currency_code: str` |

For `ProductResponse`, two reasonable approaches:
- **Simple (now):** resolve the active PKR price server-side and return `price_amount: int` — frontend sees no structural change
- **Full (later):** return `prices: list[ProductPriceResponse]` and let the frontend pick by currency

Start with simple. The rename `price` → `price_amount` is the only breaking change the
frontend notices.

### Price Resolution Service

Extract the price lookup into a shared function — called by product reads, order creation,
and future Stripe endpoints. **Uses the synchronous `Session`** (this codebase has no
async SQLAlchemy setup):

```python
# src/services/pricing.py
from sqlalchemy.orm import Session
from sqlalchemy import or_
from sqlalchemy.sql import func
from fastapi import HTTPException
from uuid import UUID
from src.models.product_price import ProductPrice

def resolve_price(
    db: Session,
    product_id: UUID,
    currency_code: str = "PKR",
) -> int:
    """
    Returns the active price amount (in minor units) for a product/currency pair.

    Selection rules:
    - is_active = True
    - valid_from is NULL (permanent price) OR valid_from <= now() (scheduled price that has started)
    - valid_until is NULL (no expiry) OR valid_until > now() (not yet expired)
    - If multiple rows match (e.g. overlapping scheduled prices), take the one with the
      latest valid_from (most recently activated), NULLs last.

    Raises HTTP 404 if no active price exists.
    """
    price = (
        db.query(ProductPrice)
        .filter(
            ProductPrice.product_id == product_id,
            ProductPrice.currency_code == currency_code,
            ProductPrice.is_active == True,
            or_(ProductPrice.valid_from == None, ProductPrice.valid_from <= func.now()),
            or_(ProductPrice.valid_until == None, ProductPrice.valid_until > func.now()),
        )
        .order_by(ProductPrice.valid_from.desc().nullslast())
        .first()
    )
    if not price:
        raise HTTPException(
            status_code=404,
            detail=f"No active price for product {product_id} in {currency_code}",
        )
    return price.amount
```

Both `valid_from <= now()` and `valid_until > now()` filters are required:
- Without `valid_from <= now()`: future-scheduled prices leak into current results.
- Without `valid_until > now()`: expired sale prices are still served.

### CRUD / Endpoint Changes

**Products (`src/routes/products/`):**
- `POST /products` — accept `price_amount: int`, create a `ProductPrice` row alongside
  the product in the same transaction
- `PUT /products/{id}` — updating price updates the single active `ProductPrice` row
  (simpler; price history via `valid_from`/`valid_until` is a deferred feature)
- `GET /products` / `GET /products/{id}` — must join `product_prices` to resolve the
  active price

**Price filter complexity (previously `Product.price >= min_price`):**

The `min_price` / `max_price` query params currently filter with `Product.price >= min_price`
directly. Once `price` moves to `product_prices`, this requires a correlated subquery:

```python
from sqlalchemy import select as sa_select

def _active_price_subquery(currency_code: str = "PKR"):
    return (
        sa_select(ProductPrice.amount)
        .where(
            ProductPrice.product_id == Product.id,
            ProductPrice.currency_code == currency_code,
            ProductPrice.is_active == True,
            or_(ProductPrice.valid_from == None, ProductPrice.valid_from <= func.now()),
            or_(ProductPrice.valid_until == None, ProductPrice.valid_until > func.now()),
        )
        .order_by(ProductPrice.valid_from.desc().nullslast())
        .limit(1)
        .correlate(Product)
        .scalar_subquery()
    )

# In get_products():
if min_price is not None:
    query = query.filter(_active_price_subquery() >= min_price)
if max_price is not None:
    query = query.filter(_active_price_subquery() <= max_price)
```

This subquery is also used to populate `price_amount` in the response, so extract it once
and reuse rather than duplicating.

**Cart service (`src/routes/carts/service.py`) — currently missing from plan:**

The cart service accesses `product.price` directly (e.g. line 46: `price=product.price`).
This will raise `AttributeError` at runtime once `products.price` is dropped. Update it to
call `resolve_price(db, product.id)` in the same way as order creation.

**Orders (`src/routes/orders/`):**
- `POST /orders` (the existing endpoint, `source="whatsapp"` is passed in body — there is
  no separate `/orders/whatsapp` endpoint) — call `resolve_price()` per item, compute
  `total_amount` server-side, snapshot `unit_amount` on each `OrderItem`. Never trust a
  price from the client.
- Future `POST /orders/stripe/create-intent` — identical price resolution, then call
  Stripe with `total_amount` and `currency_code`.

### Seeders

**`CurrencySeeder`** (new, must run before `ProductSeeder`):

```python
class CurrencySeeder(BaseSeeder):
    def run(self):
        if not self.db.query(Currency).filter_by(code="PKR").first():
            self.db.add(Currency(code="PKR", decimal_places=2, is_default=True))
            self.db.commit()
```

**`ProductSeeder`** — add a `ProductPrice` row for each product:

```python
# After inserting a product:
db.add(ProductPrice(
    product_id=product.id,
    currency_code="PKR",
    amount=150000,   # Rs 1,500.00
    is_active=True,
    valid_from=None,   # permanent price
    valid_until=None,
))
```

---

## Layer 3 — Frontend

### 1. Create `src/lib/currency.ts`

```typescript
export type SupportedCurrency = "PKR" | "USD" | "EUR";

const CURRENCY_CONFIG: Record<SupportedCurrency, { locale: string; decimalPlaces: number }> = {
  PKR: { locale: "en-PK", decimalPlaces: 2 },
  USD: { locale: "en-US", decimalPlaces: 2 },
  EUR: { locale: "en-IE", decimalPlaces: 2 },
};

export const formatPrice = (
  amount: number,
  currency: SupportedCurrency = "PKR"
): string => {
  const { locale, decimalPlaces } = CURRENCY_CONFIG[currency];
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
    minimumFractionDigits: decimalPlaces,
    maximumFractionDigits: decimalPlaces,
  }).format(amount / 100);
};
```

`Intl.NumberFormat` handles the Rs symbol, number grouping, and decimal places automatically
for each locale. No manual symbol prefix needed.

### 2. Update RTK Query types

| Old | New |
|---|---|
| `product.price` | `product.price_amount` |
| `order.total_cents` | `order.total_amount` |
| `orderItem.price_cents` | `orderItem.unit_amount` |

Also add `currency_code: string` to `Order` and `Payment` types.

### 3. Replace all local `formatPrice` functions

Every file that has a local `formatPrice`:

```
ProductInfo.tsx
ShoppingBag.tsx
ProductGrid.tsx
admin/orders/[id]/page.tsx
account/orders/[id]/page.tsx
admin/orders/page.tsx
account/orders/page.tsx
whatsapp.ts
```

In each: delete the local function, add `import { formatPrice } from "@/lib/currency"`,
update field references (`price` → `price_amount`, `price_cents` → `unit_amount`, etc.).

### 4. Fix `CurrencyField.tsx`

Remove the manual `currencySymbol` prop approach entirely. Derive the symbol from `Intl`
using the same `formatPrice` utility, or at minimum change the default from `"€"` → `"Rs"`.
The internal paisa storage (`/100` on display, `* 100` on save) does not change.

### 5. Fix `PRICE_OPTIONS` in category page

```typescript
const PRICE_OPTIONS = [
  { label: "Under Rs 500",        values: { max: 50000 } },
  { label: "Rs 500 – Rs 2,000",   values: { min: 50000,  max: 200000 } },
  { label: "Rs 2,000 – Rs 5,000", values: { min: 200000, max: 500000 } },
  { label: "Over Rs 5,000",       values: { min: 500000 } },
];
```

Values are in paisa. Ranges adjusted for a PKR wallet/accessory store.

### 6. Leave `checkout/page.tsx` alone

Still mock data, not connected to real cart state. Needs a full rewrite as a separate task.
The currency issue is the least of its problems.

---

## Layer 4 — Deferred (Don't Build Now)

| Feature | When to build |
|---|---|
| Multi-currency frontend (currency switcher, user preference) | When you add a second currency to `product_prices` |
| `decimal_places` used dynamically in `formatPrice` | When you add a zero-decimal currency (JPY) or 3-decimal (KWD) |
| Stripe payment intent endpoint | When you're ready to go live with card payments |
| Sale pricing UI (set `valid_from`/`valid_until` in admin) | When you want admin-scheduled sales |
| `product_prices` returned as array in API response | When frontend needs to display multiple currencies |
| Price history preservation on update | When audit trail matters (currently: update in place) |

---

## Execution Order

```
1.  Migration 1              ← currencies table (table must exist before seeder runs)
2.  CurrencySeeder           ← seeds PKR row (unblocks ProductSeeder)
3.  Migration 2              ← product_prices table + partial unique index + drop products.price
4.  Migration 3              ← rename orders/order_items/payments columns + add currency_code
5.  Update SQLAlchemy models ← Currency, ProductPrice (new); Product, Order, OrderItem, Payment (updated)
6.  Update Pydantic schemas  ← field renames across all route schemas
7.  pricing.py service       ← resolve_price() with both valid_from and valid_until guards
8.  Update product CRUD      ← GET uses subquery for price; POST/PUT touch product_prices
9.  Update cart service      ← replace product.price access with resolve_price()
10. Update order creation    ← resolve_price() per item, total computed server-side
11. Update ProductSeeder     ← seeds ProductPrice rows after products
12. src/lib/currency.ts      ← frontend utility
13. Update RTK Query types   ← field renames + add currency_code to Order/Payment
14. Replace formatPrice()    ← all 8 frontend files
15. Fix CurrencyField.tsx
16. Fix PRICE_OPTIONS
```

Steps 1–11 are backend (one PR). Steps 12–16 are frontend (follow immediately after).
