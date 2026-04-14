import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Make sure the app package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings
from app.database import Base

# Import every model so Alembic can see all tables for autogenerate
from app.models import user, health_data, lab_test, integration  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Point Alembic at our SQLAlchemy metadata
target_metadata = Base.metadata


def get_url() -> str:
    """Read DATABASE_URL from settings (or environment, for CI/CD pipelines)."""
    return os.environ.get("DATABASE_URL") or get_settings().database_url


def run_migrations_offline() -> None:
    """Run migrations without a live DB connection (generates SQL script)."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live DB connection."""
    ini_section = config.get_section(config.config_ini_section, {})
    ini_section["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        ini_section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
