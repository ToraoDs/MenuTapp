from logging.config import fileConfig
import os

from sqlalchemy import engine_from_config, pool

from alembic import context

from app import models  # noqa: F401  (registra las tablas en Base.metadata)
from app.database import Base, DATABASE_URL

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

url = os.getenv("DATABASE_URL", DATABASE_URL)
config.set_main_option("sqlalchemy.url", url)


def _configure(connection=None) -> None:
    kwargs = {
        "target_metadata": target_metadata,
        "render_as_batch": url.startswith("sqlite"),
        "transactional_ddl": True,
        "compare_type": True,
    }
    if connection is not None:
        kwargs["connection"] = connection
    context.configure(**kwargs)


def run_migrations_offline() -> None:
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=url.startswith("sqlite"),
        transactional_ddl=True,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        if url.startswith("sqlite"):
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
            connection.commit()
        _configure(connection)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
