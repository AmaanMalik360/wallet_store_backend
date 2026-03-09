# Database Migration Commands

This document contains all the commands needed to set up and run database migrations for your e-commerce application using Alembic with manual migration creation (similar to Sequelize workflow).

## Prerequisites

1. Make sure PostgreSQL is running and accessible
2. Update your `.env` file with correct database credentials
3. Install dependencies: `uv sync`
4. Ensure `alembic/env.py` is configured to use your database URL from settings

## Migration Creation Workflow

### Step 1: Create Empty Migration File
```bash
alembic revision -m "Descriptive message about the migration"
```

### Step 2: Edit the Generated Migration File
- Navigate to `alembic/versions/` directory
- Find the newly created migration file (with timestamp prefix)
- Edit the `upgrade()` and `downgrade()` functions manually

### Step 3: Apply the Migration
```bash
alembic upgrade head
```

## Recommended Migration Commands

### 1. Create Users Table Migration
```bash
# Create empty migration
alembic revision -m "Create users table"

# Then edit the generated file to include:
# - users table with UUID primary key
# - email, password_hash, name, is_guest fields
# - created_at and updated_at timestamps
# - Unique constraint on email
# - Index on email field
```

## Migration Management Commands

### Check Current Migration Status
```bash
alembic current
```

### View Migration History
```bash
alembic history
```

### Run All Migrations
```bash
alembic upgrade head
```

### Run Specific Migration
```bash
alembic upgrade <revision_id>
```

### Rollback Commands

#### Rollback to Previous Migration
```bash
alembic downgrade -1
```

#### Rollback to Specific Migration
```bash
alembic downgrade <revision_id>
```

#### Rollback All Migrations
```bash
alembic downgrade base
```

#### Reset Migration Base
```bash
alembic stamp base
```

## Alternative: Autogenerate Approach (Optional)

If you prefer automatic migration generation (less control but faster):

```bash
alembic revision --autogenerate -m "Create all e-commerce tables"
```

**Note**: This requires your models to be properly imported in `alembic/env.py` and may create all tables in one migration.

## Database Operations

### Test Database Connection
```bash
python -c "from models.db import db_manager; print('Connected' if db_manager.test_connection() else 'Failed')"
```

### Reset Database (Drop and Recreate)
```bash
# WARNING: This will delete all data!
alembic downgrade base
alembic upgrade head
```

## Important Configuration Notes

### alembic/env.py Setup
Your `alembic/env.py` should be configured to:
1. Import your settings and models
2. Set the database URL from your configuration
3. Use proper SQLAlchemy engine configuration

### Migration File Structure
Each migration file should include:
- **upgrade()** function: Applies the migration
- **downgrade()** function: Reverts the migration
- Proper revision identifiers
- SQLAlchemy operations (create_table, add_column, etc.)

## Best Practices

1. **Descriptive Messages**: Always use clear, descriptive migration messages
2. **Review Before Applying**: Check generated migration files before running them
3. **Test Migrations**: Test migrations in development before production
4. **Backup Database**: Always backup before major migrations
5. **Incremental Changes**: Keep migrations small and focused

## Troubleshooting

### Common Issues

#### Database Connection Errors
- Check PostgreSQL is running
- Verify database credentials in `.env`
- Ensure database exists

#### Migration Already Applied
```bash
# Check current status
alembic current

# If stuck, try forcing the revision
alembic stamp <revision_id>
```

#### Foreign Key Constraint Errors
- Ensure dependent tables are created first
- Check ON DELETE actions are appropriate
- Verify data types match between tables

#### Migration File Not Found
- Check file is in `alembic/versions/` directory
- Verify filename format (timestamp + message)
- Ensure proper Python syntax

### If Autogenerate Shows No Changes
- Make sure models are imported in `alembic/env.py`
- Check database URL is correctly configured
- Verify models have proper SQLAlchemy annotations

### To Regenerate a Migration
```bash
# Rollback the migration first
alembic downgrade -1

# Remove the migration file manually
rm alembic/versions/xxxx_migration_file.py

# Generate it again
alembic revision -m "Your message"
```

## Migration File Example

Here's a template for reference:

```python
"""Create users table

Revision ID: abc123def456
Revises: 
Create Date: 2024-01-15 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'abc123def456'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=True),
        sa.Column('is_guest', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

def downgrade() -> None:
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
```
