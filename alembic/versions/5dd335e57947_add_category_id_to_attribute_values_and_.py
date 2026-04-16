"""Add category_id to attribute_values and create category_attributes table for Path B

Revision ID: 5dd335e57947
Revises: e16bc5fb6fb2
Create Date: 2026-04-14 02:32:45.037043

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5dd335e57947'
down_revision: Union[str, Sequence[str], None] = 'e16bc5fb6fb2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add category_id column to attribute_values
    op.add_column('attribute_values',
        sa.Column('category_id', sa.Integer(), nullable=True)
    )
    
    # Add foreign key constraint for category_id
    op.create_foreign_key(
        'fk_attribute_values_category_id',
        'attribute_values', 'categories',
        ['category_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # Create unique constraint on (attribute_id, category_id, value)
    op.create_unique_constraint(
        'uq_attr_value_per_category',
        'attribute_values',
        ['attribute_id', 'category_id', 'value']
    )
    
    # Create category_attributes junction table
    op.create_table('category_attributes',
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.Column('attribute_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['attribute_id'], ['attributes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('category_id', 'attribute_id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop category_attributes table
    op.drop_table('category_attributes')
    
    # Drop unique constraint from attribute_values
    op.drop_constraint('uq_attr_value_per_category', 'attribute_values', type_='unique')
    
    # Drop foreign key constraint for category_id
    op.drop_constraint('fk_attribute_values_category_id', 'attribute_values', type_='foreignkey')
    
    # Remove category_id column from attribute_values
    op.drop_column('attribute_values', 'category_id')
