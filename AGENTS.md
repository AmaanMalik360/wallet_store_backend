# Backend — Scale & Senew (FastAPI)

## Role

API backend for a wallets/bags e-commerce storefront and admin dashboard. WhatsApp is the primary checkout channel (`orders` module defaults `source="whatsapp"`). Stack: FastAPI, SQLAlchemy 2.0 (`mapped_column`), PostgreSQL, Alembic (manual-first migrations), pydantic-settings, pwdlib, uv.

## Layout

```
backend/
├── main.py            # App entry: CORS, lifespan, static files, register_routes
├── core/config.py     # Settings via pydantic-settings (.env)
├── src/
│   ├── api.py         # register_routes() — includes all routers
│   ├── auth/          # JWT + FastAPI dependencies
│   ├── models/        # SQLAlchemy models
│   ├── middleware/     # ImageUploadMiddleware
│   ├── services/       # Cross-route business logic (pricing.py)
│   └── routes/         # addresses, admin, attribute_values, attributes,
│                        # carts, categories, orders, payments (stub),
│                        # products, shipments (stub), users
├── alembic/            # DB migrations
└── seeders/            # Seed scripts
```

## Request flow & conventions

Controller → Service → SQLAlchemy Models, with a `{ success, message, data }` response envelope on every route. The full behavioral pattern (error handling, pagination, eager loading, replace-on-assign, logging) is defined in `.devin/rules/backend.md` — follow it for all new routes. Schema conventions (PK types, FK `ondelete`, monetary minor units, timestamps, slugs) are in `.devin/rules/database.md`.

## Route modules

| Module | Prefix | Auth |
|--------|--------|------|
| `users` | `/api/v1/users` | Mixed (guest/registered/none) |
| `carts` | `/api/v1/cart` | `CurrentUser` (all) |
| `products` | `/api/v1/products` | None (public) |
| `categories` | `/api/v1/categories` | None (public reads) |
| `attributes` | `/api/v1/attributes` | None |
| `attribute_values` | `/api/v1/attribute-values` | None |
| `orders` | `/api/v1/orders` | `CurrentUser` (customer) / `admin:access` (admin) |
| `addresses` | `/api/v1/addresses` | `CurrentUser` |
| `admin` | `/api/v1/admin` | `require_permission("roles:manage")` |
| `payments`, `shipments` | — | **Stub** — directories exist, no controller/service implemented |

## Config essentials (`core/config.py`)

- `api_v1_prefix: "/api/v1"`
- `access_token_expire_minutes: 30`, `guest_token_expire_days: 30`, `refresh_token_expire_days: 7`
- `cookie_secure: False` (dev) — set `True` in production
- `auto_create_tables: False` — schema is managed via Alembic
- `allowed_origins: ["http://localhost:3000"]`

## Domain modules

Each domain (categories, EAV attributes, products/pricing, auth, rbac, users, cart, orders/addresses, payments/shipments) has its own ownership and cross-module coupling documented in `agents/modules/index.md`. Read it before changing anything that touches more than one route module.
