"""initial schema

Revision ID: 0001_initial
Revises: 
Create Date: 2025-09-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'states',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=100), nullable=False, unique=True),
        sa.Column('uf', sa.String(length=2), nullable=False, unique=True),
    )

    op.create_table(
        'municipalities',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('state_id', sa.Integer(), sa.ForeignKey('states.id'), nullable=False),
    )

    op.create_table(
        'document_types',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=100), nullable=False, unique=True),
    )

    op.create_table(
        'orgaos',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('tipo', sa.String(length=50), nullable=False),
        sa.Column('state_id', sa.Integer(), sa.ForeignKey('states.id')),
        sa.Column('municipality_id', sa.Integer(), sa.ForeignKey('municipalities.id')),
    )

    op.create_table(
        'documents',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('title', sa.String(length=300), nullable=False),
        sa.Column('url', sa.Text(), nullable=True),
        sa.Column('publication_date', sa.Date(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('orgao_id', sa.Integer(), sa.ForeignKey('orgaos.id')),
        sa.Column('document_type_id', sa.Integer(), sa.ForeignKey('document_types.id')),
        sa.Column('state_id', sa.Integer(), sa.ForeignKey('states.id')),
        sa.Column('municipality_id', sa.Integer(), sa.ForeignKey('municipalities.id')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('documents')
    op.drop_table('orgaos')
    op.drop_table('document_types')
    op.drop_table('municipalities')
    op.drop_table('states')

