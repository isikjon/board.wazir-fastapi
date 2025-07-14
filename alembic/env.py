from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Import the project's settings and database URL
from database import Base
import os

# Используем URL из переменной окружения или значение по умолчанию
database_url = os.environ.get('DATABASE_URL')
if not database_url:
    # Экранируем % символы для ConfigParser
    database_url = 'mysql+pymysql://wazir:c%%3AICx9Pr%%7B48y%%3E6BmBc3r@91.218.141.27/wazir'

config.set_main_option('sqlalchemy.url', database_url)

# Import all models
from app.models.user import User, UserRole, UserStatus
from app.models.property import Property, PropertyImage, Category, Favorite, PropertyStatus, PropertyCategory
from app.models.message import Message, MessageStatus
from app.models.request import Request, RequestStatus, RequestType
from app.models.chat import AppChatModel, AppChatMessageModel
from app.models.chat_message import ChatMessage
from app.models.support import TicketStatus, SupportTicket, TicketResponse

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    configuration = config.get_section(config.config_ini_section)
    if not configuration:
        configuration = {}
    
    # Используем URL из переменной окружения или значение по умолчанию
    url = os.environ.get('DATABASE_URL')
    if not url:
        # Экранируем % символы для ConfigParser
        url = 'mysql+pymysql://wazir:c%%3AICx9Pr%%7B48y%%3E6BmBc3r@91.218.141.27/wazir'
    
    configuration["sqlalchemy.url"] = url
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online() 