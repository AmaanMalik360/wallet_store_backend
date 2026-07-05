"""Add RBAC tables (roles, permissions, role_permissions, user_roles)

Revision ID: a1b2c3d4e5f6
Revises: f1a2b3c4d5e6
Create Date: 2026-06-21 23:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create roles table
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(50), nullable=False, unique=True),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create permissions table
    op.create_table(
        "permissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Create role_permissions junction table
    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("permission_id", sa.Integer(), sa.ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
    )

    # Create user_roles junction table
    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Seed default roles and permissions
    op.execute("""
        INSERT INTO roles (name, description) VALUES
        ('super_admin', 'Full system access'),
        ('admin', 'Administrative access'),
        ('moderator', 'Content moderation access');
    """)

    op.execute("""
        INSERT INTO permissions (name, description) VALUES
        ('admin:access', 'Access admin panel'),
        ('products:create', 'Create products'),
        ('products:read', 'View products'),
        ('products:update', 'Update products'),
        ('products:delete', 'Delete products'),
        ('categories:create', 'Create categories'),
        ('categories:read', 'View categories'),
        ('categories:update', 'Update categories'),
        ('categories:delete', 'Delete categories'),
        ('orders:read', 'View orders'),
        ('orders:update', 'Update order status'),
        ('users:read', 'View users'),
        ('users:manage', 'Manage users'),
        ('roles:manage', 'Manage roles and permissions');
    """)

    # Assign all permissions to super_admin
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r, permissions p WHERE r.name = 'super_admin';
    """)

    # Assign common admin permissions to admin role
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r, permissions p 
        WHERE r.name = 'admin' 
        AND p.name IN (
            'admin:access',
            'products:create', 'products:read', 'products:update', 'products:delete',
            'categories:create', 'categories:read', 'categories:update', 'categories:delete',
            'orders:read', 'orders:update'
        );
    """)

    # Assign read-only permissions to moderator
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r, permissions p 
        WHERE r.name = 'moderator' 
        AND p.name IN ('admin:access', 'products:read', 'categories:read', 'orders:read');
    """)


def downgrade() -> None:
    op.drop_table("user_roles")
    op.drop_table("role_permissions")
    op.drop_table("permissions")
    op.drop_table("roles")
