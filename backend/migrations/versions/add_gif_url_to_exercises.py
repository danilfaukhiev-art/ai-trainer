"""add gif_url to exercises

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-02-18

"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('exercises', sa.Column('gif_url', sa.String(512), nullable=True))


def downgrade() -> None:
    op.drop_column('exercises', 'gif_url')
