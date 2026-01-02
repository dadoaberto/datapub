"""add state region fields

Revision ID: 0003_add_state_region_fields
Revises: 0002_add_ibge_ids
Create Date: 2025-09-20 00:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '0003_add_state_region_fields'
down_revision = '0002_add_ibge_ids'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('states', sa.Column('region_name', sa.String(length=50), nullable=True))
    op.add_column('states', sa.Column('region_code', sa.String(length=2), nullable=True))


def downgrade() -> None:
    op.drop_column('states', 'region_code')
    op.drop_column('states', 'region_name')

