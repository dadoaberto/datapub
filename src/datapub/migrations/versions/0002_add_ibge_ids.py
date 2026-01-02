"""add ibge ids

Revision ID: 0002_add_ibge_ids
Revises: 0001_initial
Create Date: 2025-09-20 00:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '0002_add_ibge_ids'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('states', sa.Column('ibge_id', sa.Integer(), nullable=True))
    op.create_unique_constraint('uq_states_ibge_id', 'states', ['ibge_id'])

    op.add_column('municipalities', sa.Column('ibge_id', sa.Integer(), nullable=True))
    op.create_unique_constraint('uq_municipalities_ibge_id', 'municipalities', ['ibge_id'])


def downgrade() -> None:
    op.drop_constraint('uq_municipalities_ibge_id', 'municipalities', type_='unique')
    op.drop_column('municipalities', 'ibge_id')

    op.drop_constraint('uq_states_ibge_id', 'states', type_='unique')
    op.drop_column('states', 'ibge_id')

