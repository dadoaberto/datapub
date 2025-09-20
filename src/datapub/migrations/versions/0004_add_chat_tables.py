"""add chat tables

Revision ID: 0004_add_chat_tables
Revises: 0003_add_state_region_fields
Create Date: 2025-09-20 12:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '0004_add_chat_tables'
down_revision = '0003_add_state_region_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'chat_sessions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('title', sa.String(length=200), nullable=True),
        sa.Column('entity', sa.String(length=50), nullable=True),
        sa.Column('estado', sa.String(length=2), nullable=True),
        sa.Column('municipio', sa.String(length=150), nullable=True),
        sa.Column('orgao', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        'chat_messages',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('session_id', sa.Integer(), sa.ForeignKey('chat_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_chat_messages_session_created', 'chat_messages', ['session_id', 'created_at'])


def downgrade() -> None:
    op.drop_index('ix_chat_messages_session_created', table_name='chat_messages')
    op.drop_table('chat_messages')
    op.drop_table('chat_sessions')

