"""merge_migrations

Revision ID: 77727a9fb889
Revises: d7e8f9a01234, add_panorama_fields
Create Date: 2025-06-11 01:52:42.150282

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '77727a9fb889'
down_revision = ('d7e8f9a01234', 'add_panorama_fields')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass 