
Paste the following into [backend/README.md](cci:7://file:///c:/Users/Baller/Desktop/hub.com/wallet-store-lovable-version/backend/README.md:0:0-0:0):

```markdown
# Wallet Store Backend (FastAPI)

FastAPI backend for the Wallet Store application using:

- **FastAPI**
- **SQLAlchemy 2.0**
- **PostgreSQL**
- **Alembic** (manual-first migrations)
- **uv** (dependency management + running)

## Requirements

- **Python**: `>= 3.12` (see [pyproject.toml](cci:7://file:///c:/Users/Baller/Desktop/hub.com/wallet-store-lovable-version/backend/pyproject.toml:0:0-0:0))
- **PostgreSQL**: running locally or reachable over the network

## Project Structure (high level)

- **[main.py](cci:7://file:///c:/Users/Baller/Desktop/hub.com/wallet-store-lovable-version/backend/main.py:0:0-0:0)**
  - Creates the FastAPI app
  - Loads settings from `core/config.py`
  - Initializes DB connection on startup and creates tables (`db_manager.create_tables()`)
  - Registers API routes via [src/api.py](cci:7://file:///c:/Users/Baller/Desktop/hub.com/wallet-store-lovable-version/backend/src/api.py:0:0-0:0)
- **`core/config.py`**
  - Central configuration using `pydantic-settings`
  - Reads `.env` and exposes `settings.database_url` / `settings.async_database_url`
- **`src/models/db.py`**
  - SQLAlchemy engine/session factory
  - `get_db()` dependency for request-scoped sessions
- **`alembic/`**
  - Alembic configuration (configured to use `settings.database_url` in [alembic/env.py](cci:7://file:///c:/Users/Baller/Desktop/hub.com/wallet-store-lovable-version/backend/alembic/env.py:0:0-0:0))
- **`seeders/`**
  - Seeder runner + individual seeders (e.g. `category_seeder.py`)

## Setup

### 1) Install dependencies

```bash
uv sync
```

### 2) Configure environment variables

Create a `.env` file in the project root (same level as [main.py](cci:7://file:///c:/Users/Baller/Desktop/hub.com/wallet-store-lovable-version/backend/main.py:0:0-0:0)).

You can start from [.env.example](cci:7://file:///c:/Users/Baller/Desktop/hub.com/wallet-store-lovable-version/backend/.env.example:0:0-0:0):

```bash
copy .env.example .env
```

Key variables (see [.env.example](cci:7://file:///c:/Users/Baller/Desktop/hub.com/wallet-store-lovable-version/backend/.env.example:0:0-0:0) and `core/config.py`):

```env
DB_HOSTNAME=localhost
DB_PORT=5432
DB_NAME=fastapi_db
DB_USERNAME=postgres
DB_PASSWORD=your_password_here

APP_NAME=FastAPI Application
APP_VERSION=1.0.0
DEBUG=false

JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

API_V1_PREFIX=/api/v1

# comma-separated
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080
```

Notes:

- `core/config.py` uses `SettingsConfigDict(env_file=".env")`.
- `src/models/db.py` builds the SQLAlchemy engine from `settings.database_url`.

## Running the API

The app entrypoint is `main:app`.

### Development

```bash
uv run python -m uvicorn main:app --reload
```

### Start

```bash
uv run python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### Production

```bash
uv run python -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

On startup, [main.py](cci:7://file:///c:/Users/Baller/Desktop/hub.com/wallet-store-lovable-version/backend/main.py:0:0-0:0) will:

- Validate DB connectivity (`db_manager.test_connection()`)
- Create tables (`db_manager.create_tables()`)

Useful endpoints:

- `GET /` basic app info
- `GET /health` health check including DB connectivity

## API Routes

Routes are registered in [src/api.py](cci:7://file:///c:/Users/Baller/Desktop/hub.com/wallet-store-lovable-version/backend/src/api.py:0:0-0:0).

### Users

Base path: [/users](cci:9://file:///users:0:0-0:0)

- `POST /users`
- `GET /users`
- `GET /users/{user_id}`
- `PUT /users/{user_id}`
- `DELETE /users/{user_id}`
- `GET /users/email/{email}`

## Database Migrations (Alembic)

This project supports a **manual-first** migration workflow (similar to Sequelize): create a revision, then edit `upgrade()` / `downgrade()`.

Full reference: [MIGRATION_COMMANDS.md](cci:7://file:///c:/Users/Baller/Desktop/hub.com/wallet-store-lovable-version/backend/MIGRATION_COMMANDS.md:0:0-0:0).

Common commands:

```bash
# create empty migration
alembic revision -m "Your message"

# apply all migrations
alembic upgrade head

# check current revision
alembic current

# rollback one migration
alembic downgrade -1
```

Alembic is configured to use the database URL from settings:

- [alembic/env.py](cci:7://file:///c:/Users/Baller/Desktop/hub.com/wallet-store-lovable-version/backend/alembic/env.py:0:0-0:0) imports `settings` and sets `sqlalchemy.url` to `settings.database_url`.

## Seeding Data

Seeders live in `seeders/`. The runner supports:

- listing seeders
- running one seeder by filename
- running all seeders
- optional `--clear` support (if the seeder implements `clear()`)

Examples:

```bash
# list available seeders
uv run python seeders/run_seeders.py --list

# run all seeders
uv run python seeders/run_seeders.py --all

# clear + run all seeders
uv run python seeders/run_seeders.py --all --clear

# run a specific seeder (filename)
uv run python seeders/run_seeders.py category_seeder.py
```

## Troubleshooting

### Database connection fails at startup

- Ensure PostgreSQL is running
- Ensure the database exists (`DB_NAME`)
- Verify `.env` values match your DB credentials
- Confirm the connection info in `core/config.py` (`settings.database_url`)

### Migrations don’t run / env not loaded

- Ensure `.env` exists at the project root
- [alembic/env.py](cci:7://file:///c:/Users/Baller/Desktop/hub.com/wallet-store-lovable-version/backend/alembic/env.py:0:0-0:0) loads `settings.database_url` directly; confirm it points to the correct DB

### CORS issues

- Update `ALLOWED_ORIGINS` in `.env` (comma-separated)
- Restart the server after changing `.env`
```

## Status

- **README content prepared** and ready to paste into [README.md](cci:7://file:///c:/Users/Baller/Desktop/hub.com/wallet-store-lovable-version/backend/README.md:0:0-0:0).