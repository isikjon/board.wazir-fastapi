"""Add media fields to properties

Revision ID: add_media_fields
Revises: 
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'add_media_fields'
down_revision = None  # Установите предыдущую ревизию если есть
branch_labels = None
depends_on = None


def upgrade():
    # Добавляем новые поля для медиа-сервера
    op.add_column('properties', sa.Column('media_id', sa.String(19), nullable=True))
    op.add_column('properties', sa.Column('images_data', sa.JSON(), nullable=True))
    
    # Создаем индекс для media_id
    op.create_index('ix_properties_media_id', 'properties', ['media_id'])
    

def downgrade():
    # Удаляем индекс и поля
    op.drop_index('ix_properties_media_id', table_name='properties')
    op.drop_column('properties', 'images_data')
    op.drop_column('properties', 'media_id') 