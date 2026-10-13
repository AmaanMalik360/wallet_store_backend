# Backend Modules

Each section: what the module owns, then an **Interdependencies** list. The interdependency bullets exist because a change that looks safe in one module can silently break a flow in another — read the relevant bullets before touching shared data (users, cart, pricing).

---

## auth

**Owns:** Cookie-based JWT auth. All tokens are HttpOnly cookies — frontend never touches them directly.

**JWT (`src/auth/jwt.py`):**

- `create_access_token(user_id, is_guest)` — short-lived (30 min default)
- `create_guest_token(user_id)` — long-lived (30 days default)
- `create_refresh_token(user_id)` — 7 days, scoped to `/api/v1/users/refresh` path
- `decode_token(token)` → `TokenPayload` with `.sub` (user UUID) and `.type` (`"access"`|`"refresh"`)

**Dependencies (`src/auth/dependencies.py`):**

- `get_optional_user` — returns `User` or `None` (no auth required)
- `get_current_user` — requires valid access token (guests OK); raises 401
- `get_current_active_user` — requires non-guest registered user; raises 403 for guests
- `get_user_permissions(db, user_id)` → `set[str]` — traverses `UserRole → RolePermission → Permission`
- `require_permission(permission: str)` — factory returning a FastAPI dependency for RBAC
- `require_any_permission(*permissions)` — OR-based permission check
- Type aliases: `CurrentUser`, `CurrentActiveUser`, `OptionalUser`

**Token extraction order:** HttpOnly cookie `access_token` → `Authorization: Bearer` header.

**Settings (`core/config.py`):** `access_token_expire_minutes: 30`, `guest_token_expire_days: 30`, `refresh_token_expire_days: 7`, `cookie_secure: False` in dev (must be `True` in production).

**Interdependencies:**
- **users** — every dependency here resolves a `User` row; the guest/registered distinction (`is_guest`) lives on the `User` model, not in the token itself.
- **rbac** — `get_user_permissions()` traverses `UserRole → RolePermission → Permission`; `require_permission()`/`require_any_permission()` are the only gate for admin routes.
- **carts / orders / addresses** — every endpoint in these modules is gated by `CurrentUser`; a change to token decode logic here affects all of them simultaneously.

---

## users

**User model:**

```python
class User(Base):
    id: UUID PK (uuid7)
    email: Optional[str] = String(255), unique, nullable, index
    password: Optional[str] = String(255), nullable
    name: Optional[str]
    is_guest: bool
    guest_expires_at: Optional[DateTime]
```

`email`/`password` are nullable to support future OAuth social login. **OAuth is NOT yet implemented** — there is no `UserOAuthAccount` table, no Authlib dependency, no OAuth routes.

**Endpoints (`/api/v1/users/`):**

| Endpoint | Description |
|----------|-------------|
| `POST /users/guest` | Create guest user + cart; sets long-lived `access_token` cookie |
| `POST /users/login` | Authenticate; sets `access_token` + `refresh_token` cookies |
| `POST /users/register` | Convert current guest → registered user (preserves cart); sets new cookies |
| `GET /users/me` | Get current user with permissions |
| `POST /users/refresh` | Issue new `access_token` from `refresh_token` cookie |
| `POST /users/logout` | Clear both auth cookies |

**Guest → Registered flow:** `POST /users/register` requires `CurrentUser` (existing guest session). Calls `service.convert_guest_to_user(db, current_user, registration)`, which mutates the guest `User` row **in place**: sets `email`, `password` (hashed), `name`, `is_guest=False`, clears `guest_expires_at`. Cart is preserved automatically (same `user_id`).

**Interdependencies:**
- **cart** — a guest user's cart is created with the same `user_id`. `POST /users/register` converts the guest row **in place** (same `user_id`, same row) specifically so the cart carries over automatically. If registration ever created a new `User` row instead of mutating in place, carts would silently orphan.
- **auth** — every endpoint here sets or clears the access/refresh cookies.

---

## rbac

**Models:**

- `Permission` (int PK): name follows `"resource:action"`, e.g. `"admin:access"`, `"products:create"`, `"roles:manage"`, `"users:read"`
- `Role` (int PK): e.g. `"admin"`, `"manager"`
- `RolePermission` junction (composite PK `role_id` + `permission_id`, both CASCADE)
- `UserRole` junction: `(user_id UUID, role_id int)` composite PK
- Admin routes in `/api/v1/admin/` are protected by `require_permission("roles:manage")` for role management and `admin:access` for order/product admin pages.

**Interdependencies:**
- **auth** — `require_permission()` / `require_any_permission()` depend entirely on this module's junction tables via `get_user_permissions()`.
- **admin routes, orders (admin endpoints)** — gated by `admin:access`; role management itself is gated by `roles:manage`. Misconfiguring either permission string silently locks out or opens these endpoints.

---

## categories

Categories use the **Adjacency List** pattern with self-referential relationships.

```
Fashion (parent_id=NULL)
├── Accessories (parent_id=Fashion.id)
│   ├── Wallets (parent_id=Accessories.id)
│   │   ├── Men's Wallets
│   │   └── Women's Wallets
│   └── Belts (parent_id=Accessories.id)
└── Clothing (parent_id=Fashion.id)
```

**Model (`models/category.py`):**

```python
class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(250), nullable=False, unique=True)
    parent_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    parent: Mapped["Category"] = relationship("Category", remote_side="Category.id", back_populates="children")
    children: Mapped[list["Category"]] = relationship("Category", back_populates="parent", cascade="all, delete-orphan")
```

**Tree fetching strategies (`src/routes/categories/helpers.py`):**

1. **Recursive CTE** (`fetch_subtree_category_rows(db, root_ids)`) — single PostgreSQL `WITH RECURSIVE` query fetching the entire subtree of multiple roots in one round trip. Use when you need a full subtree efficiently.
2. **ORM traversal** (`collect_subtree_rows_from_orm(category)`) — recursive `_walk()` over already-loaded `.children` relationships. Use when you already have the ORM object with relationships loaded.
3. **In-memory descendant collection** (`Category.get_all_descendant_ids(db, category_id)`) — recursive classmethod returning just IDs for a `WHERE IN` clause. Use for product filtering.

**Tree building from flat rows** — core pattern: flat rows → lookup maps → recursive build.

```python
def build_category_trees_from_subtree_rows(db, root_ids, subtree_rows, include_attributes):
    categories_by_id = {row["id"]: row for row in subtree_rows}
    children_by_parent: dict[int | None, list[int]] = defaultdict(list)
    for row in subtree_rows:
        children_by_parent[row["parent_id"]].append(row["id"])
    attrs_by_category_id = build_filterable_attributes_for_category_map(db, categories_by_id) if include_attributes else {}
    return [
        build_category_hierarchy_from_maps(root_id, categories_by_id, children_by_parent, attrs_by_category_id)
        for root_id in root_ids if root_id in categories_by_id
    ]
# build_category_hierarchy_from_maps() recurses over children_by_parent to construct nested CategoryData,
# attaching attrs_by_category_id.get(category_id, []) as filterable_attributes at each node.
```

**API behavior (must be preserved exactly):**

- `GET /categories/` (no slug) → **root categories** (`parent_id IS NULL`) with full subtrees.
- `GET /categories/?slug=fashion` (with slug) → that category's **direct children** (`trees[0].children`), **not** the category itself. The frontend category page depends on this exact shape.

**Lineage traversal (walk up to root):**

```python
def get_category_lineage_ids(db: Session, category_id: int) -> list[int]:
    # walks parent_id chain from category_id to root, collecting ids, stops at NULL parent or revisit
```

Used for computing inherited attributes and building breadcrumbs.

**Product category filtering** — always expand to descendants before filtering:

```python
# Single category slug
descendant_ids = Category.get_all_descendant_ids(db, category.id)
query = query.filter(Product.category_id.in_([category.id] + descendant_ids))

# Multiple explicit category IDs (subcategory checkboxes) — union of each id's own descendants
```

**Deletion constraint (service layer, not a DB constraint):** `delete_category()` raises HTTP 400 if `category.children` is non-empty — forces leaf-first deletion, preventing accidental cascade deletion of entire subtrees.

**Interdependencies:**
- **attributes (EAV)** — `filterable_attributes` on each `CategoryData` is built via `build_filterable_attributes_for_category_map()`, which requires category lineage. Changing lineage traversal silently changes which attributes appear as filterable.
- **products** — product category filtering expands a selected category to `[category_id] + descendant_ids`. Category deletion is blocked only if the category **has child categories** — it is NOT blocked by having products assigned (those get `category_id = NULL` via `ondelete="SET NULL"`).

---

## attributes (EAV)

A modified **EAV (Entity-Attribute-Value)** pattern with **category-scoped inheritance**, enabling dynamic filterable product attributes without schema changes.

```
Attribute (dimension) 1──N AttributeValue (allowed value) N──M ProductAttributeValue (product tag)
                                   │ category_id (optional scope)
                                   ▼
                              Category  (assigned via CategoryAttribute)
```

**Layer 1 — `Attribute`:** globally unique `name` (e.g. "Color", "Material", "Size"); owns its values (`cascade="all, delete-orphan"`); assigned to categories via `CategoryAttribute`.

**Layer 2 — `AttributeValue`:** `{ id, attribute_id, value, category_id (nullable) }`.

**Scoping rule:**

| `category_id` | Scope | Visibility |
|---|---|---|
| `NULL` | Global | Visible to ALL categories that have this attribute assigned |
| e.g. `5` ("Wallets") | Category-scoped | Visible only when viewing category 5 or its descendants |

Example: a "Material" attribute can have generic global values (Leather, Canvas) plus specialty values scoped to one category (Crocodile, Python Skin → only under "Wallets").

**Layer 3 — `ProductAttributeValue`:** composite PK (`product_id`, `attribute_value_id`) — a product can have each value assigned only once; `ondelete="CASCADE"` on product delete.

**`CategoryAttribute`:** composite PK (`category_id`, `attribute_id`), both CASCADE. Declares "this category supports filtering by this attribute." **Replace-on-assign:** delete all existing rows, then insert the new set — never a partial PATCH.

**Inheritance algorithm (`build_filterable_attributes_for_category_map`):** a category inherits all attributes from its ancestors. For each category: build its lineage (walk up `parent_id`), union the direct `CategoryAttribute` assignments of every ancestor, then filter each attribute's values to `value.category_id is None or value.category_id in lineage_set`.

Example:
```
Fashion (has: Color, Style)
└── Accessories (has: Material)
    └── Wallets (has: none directly)

Viewing Wallets → inherited attributes: [Color, Style, Material]
Visible Material values: all global + any scoped to Accessories/Wallets
```

**Product filtering logic:** `attribute_value_ids` are grouped by `attribute_id`, then each group becomes a separate `Product.id IN (SELECT ... WHERE attribute_value_id IN (...))` filter. **OR within the same attribute, AND across different attributes** — e.g. `Color: Red, Blue` AND `Material: Leather` → products with (Red OR Blue) AND Leather.

**Admin flow (strict order dependency):**

1. `POST /attributes/` — create the dimension (e.g. "Color")
2. `POST /attribute-values/{attr_id}` — add allowed values, optionally scoped to a category
3. `POST /categories/{cat_id}/attributes` — assign the attribute to a category

Only after step 3 does the attribute appear as filterable for that category (and descendants). Creating attribute values before step 3 will silently produce no filterable attributes.

**Interdependencies:**
- **categories** — inheritance has no meaning without `get_category_lineage_ids()`; this module cannot be reasoned about in isolation from the category tree.
- **products** — product list filtering by `attribute_value_ids` joins through `ProductAttributeValue`. The admin 3-layer flow (create attribute → create values → assign to category) has a strict order dependency: an attribute not yet assigned to a category will not appear as filterable even if values exist.

---

## products & pricing

**Endpoints (`/api/v1/products/`):**

| Method | Route | Description |
|---|---|---|
| `POST /` | Create product | Multipart FormData; uploads images |
| `GET /` | List/filter products | Paginated, many filter params |
| `GET /{product_id}` | Get single product | Includes category + attributes + active `price_amount` |
| `PATCH /{product_id}` | Update product | Multipart; existing images as JSON string; `price_amount` updates `product_prices` |
| `DELETE /{product_id}` | Delete product | 204 No Content |

**Create (`POST /products/`):** `Form(...)` fields — `title`, `description?`, `category_id?`, `price_amount` (minor units), `stock_quantity`, `sku?`, `attribute_value_ids?: List[int]`, `images?: List[UploadFile]`. Saves images via `ImageUploadMiddleware("public/images/products")` → `/static/images/products/{uuid}.ext`. Inserts a `ProductPrice` row for the default currency (PKR) in the same transaction.

**Update (`PATCH /{product_id}`):** `images` field = JSON string of existing image URLs to keep (omit to preserve all); `new_images` = new uploads to add; final images = `existing_images + new_image_paths`. `price_amount` updates the active default `ProductPrice` row in place (no history yet).

**Filters:** `skip`/`limit` (0-1000), `category_ids`/`category_slug` (descendants auto-included), `min_price`/`max_price` (minor units), `in_stock`, `search` (title/description), `sort_by` (`featured|price-low|price-high|newest|name`), `attribute_value_ids` (OR within attr, AND across attrs).

**`Product` model (`models/product.py`):** `id` (UUID uuid7), `title`, `description?`, `category_id` FK, `stock_quantity` (default 0), `sku` (unique, nullable), `images: ARRAY(String)`, `product_prices` relationship (cascade delete), `created_at`/`updated_at`. **No `price` column** — price lives entirely in the price book.

**Price book architecture:**

- `currencies`: `code` CHAR(3) PK, `decimal_places`, `is_default` (`models/currency.py`).
- `product_prices`: `id` (uuid7), `product_id`, `currency_code`, `amount` (minor units), `is_active`, `valid_from` (NULL = permanent), `valid_until` (NULL = no expiry) (`models/product_price.py`). Partial unique index `uq_product_price_default` on `(product_id, currency_code) WHERE valid_from IS NULL AND is_active = TRUE`.
- **`resolve_price(db, product_id, currency_code="PKR")`** (`src/services/pricing.py`) — the single source of truth for an active price: `is_active = True`, `currency_code` matches, `valid_from` NULL or `<= now()`, `valid_until` NULL or `> now()`; prefers scheduled (non-NULL `valid_from`) over permanent pricing for sale pricing. Raises HTTP 422 if no active price exists. `_active_price_subquery()` is a correlated scalar subquery used for price-based sort/filter.
- Integration: `CartItemResponse.price_amount`, `OrderItem.unit_amount`, `Order.total_amount` are all resolved/computed via `resolve_price()`, never stored redundantly.

**Response shapes:**

```python
ProductResponse: id, title, description, category_id, price_amount, stock_quantity, sku, images[], created_at, updated_at
ProductAttribute: { value_id, attribute_id, name, value }
CategoryInProduct: { id, name, slug, parent_id }
ProductWithCategory(ProductResponse): category?: CategoryInProduct, attributes: List[ProductAttribute]
PaginatedProductsResponse: { data: List[ProductWithCategory], total, skip, limit }
```

**Deferred:** multi-currency storefront switcher, sale-pricing admin UI (`valid_from`/`valid_until` controls), price history/audit trail.

**Interdependencies:**
- **cart** — `CartItemResponse.price_amount` is resolved **live** via `resolve_price()` on every cart read, never stored on the cart item. A price change between add-to-cart and checkout is expected/intentional, not a bug.
- **orders** — `OrderItem.unit_amount` and `Order.total_amount` are computed **server-side** at order-creation time via `resolve_price()`. Client-submitted prices are never trusted, by design.
- **categories & attributes** — product filtering depends on both the category descendant-expansion logic and the EAV value-to-product join; breaking either silently returns wrong/empty product lists.

---

## cart

**Service functions (`routes/carts/service.py`):**

- `get_or_create_cart(db, user_id)` — fetch or create cart by `user_id`
- `get_cart_with_items(db, user_id)` — joins `Cart → CartItem → Product → Category`, resolves price via `resolve_price()`, returns `CartResponse`
- `add_or_update_item(db, user_id, product_id, quantity)` — upsert item; validates stock
- `update_item_quantity(db, user_id, product_id, quantity)` — absolute set; `quantity=0` → delete row
- `remove_item(db, user_id, product_id)` — delete `CartItem`; 404 if not found
- `clear_cart(db, user_id)` — delete all `CartItem`s for cart
- `sync_cart(db, user_id, items)` — **upsert only, never deletes**; `max(existing, incoming)` quantity
- `replace_cart(db, user_id, items)` — delete all, reinsert list; used at checkout initiation

**Endpoints (`controller.py`)** — all require `CurrentUser` (guests included):

```
GET    /cart                     → get_cart_with_items
POST   /cart/items               → add_or_update_item
PATCH  /cart/items/{product_id}  → update_item_quantity
DELETE /cart/items/{product_id}  → remove_item
DELETE /cart                     → clear_cart
POST   /cart/sync                → sync_cart
POST   /cart/replace             → replace_cart
```

**Pydantic models (`models.py`):**

```python
CartItemResponse: { product_id: UUID, title, price_amount: int, image: str, category_name: str|None, quantity }
CartResponse: { cart_id: UUID, user_id: UUID, items: list[CartItemResponse] }
AddItemRequest: { product_id: UUID, quantity: int (>=1) }
UpdateItemRequest: { quantity: int (>=1) }
SyncCartRequest: { items: list[AddItemRequest] }
```

**Interdependencies:**
- **users** — cart is keyed by `user_id`, created alongside the guest user; see the `users` module note on why guest→registered conversion must preserve `user_id`.
- **products & pricing** — cart item prices are resolved, not stored (see above).
- **orders** — `replace_cart` is invoked at checkout initiation; order creation reads the current cart's items to build `order_items`.

---

## orders & addresses

**Models:**

- `orders`: `id` (uuid7), `user_id`, `total_amount` (minor units), `currency_code` (FK, default PKR), `status` (`OrderStatus` enum, default `pending_payment`), `source` (default `"whatsapp"`), `shipping_address_id`, `billing_address_id`, `notes`, `created_at`, `updated_at`.
- `order_items`: composite PK (`order_id`, `product_id`), `quantity`, `unit_amount` (price snapshot in minor units).
- `OrderStatus`: `pending_payment`, `paid`, `processing`, `shipped`, `delivered`, `cancelled`.
- `addresses` (`models/address.py`): `id` (uuid7), `user_id`, `line1`, `line2`, `city`, `state`, `postal_code`, `country` (ISO 3166-1 alpha-2), `label`, `is_default`, `created_at`, `updated_at`. **Append-only** — "editing" creates a new row and re-points the order FK; never mutates an existing row.

**Customer endpoints (require `CurrentUser`):**

- `POST /orders` — create order from cart/items; `source` defaults to `"whatsapp"`; computes `total_amount` server-side via `resolve_price()` per item.
- `GET /orders/mine` — list orders visible to customer (paid, processing, shipped, delivered, cancelled).
- `GET /orders/mine/{order_id}` — get single customer order.

**Admin endpoints (require `admin:access`):**

- `GET /orders`, `GET /orders/{order_id}` — list (status filter + customer search) / detail.
- `PATCH /orders/{order_id}/status` — update status.
- `PUT /orders/{order_id}/items` — replace order items (recomputes total).
- `PATCH /orders/{order_id}` — update meta (shipping/billing address, notes).
- `POST /orders/{order_id}/shipment` — upsert shipment.
- `DELETE /orders/{order_id}` — delete order.

**Pricing:** order creation calls `resolve_price(db, product_id, currency_code)` (`src/services/pricing.py`). Client-submitted prices are never trusted — `unit_amount`/`total_amount` are always computed server-side.

**Address endpoints:** `GET /addresses` (list), `POST /addresses` (create), `DELETE /addresses/{id}` (delete — **blocked** if referenced by an order; application-level check, not a DB constraint).

**WhatsApp checkout (backend side):** `source: "whatsapp"` is the default on order creation; the frontend builds the `wa.me` link after the order is created (see `@/frontend/agents/modules/index.md` → `state`). No server-to-WhatsApp integration exists.

**Interdependencies:**
- **cart** — order creation consumes the current cart's items to build `order_items`.
- **products & pricing** — every order item's price is resolved server-side via `resolve_price()` at creation time; this is the module where "never trust client price" is enforced.
- **addresses** — `orders.shipping_address_id`/`billing_address_id` use `ondelete="SET NULL"`, but the address-delete endpoint explicitly blocks deletion if an order still references it (an application-level check, not a DB constraint — don't assume the DB will stop you).
- **payments / shipments (stub)** — the only working shipment interaction is `POST /orders/{order_id}/shipment`, implemented inside the orders controller itself, not a standalone shipments API.

---

## payments / shipments (stub)

**Owns:** `models/payment.py` and `models/shipment.py` exist and are referenced by `Order`, but `src/routes/payments/` and `src/routes/shipments/` are **empty directories** — no controller, service, or models.py. Treat this as reserved for future work, not an implemented module.

**Interdependencies:**
- **orders** — the one live touchpoint (`POST /orders/{order_id}/shipment`) is part of the orders module, not this one. Do not assume a parallel `/api/v1/shipments` or `/api/v1/payments` surface exists.
