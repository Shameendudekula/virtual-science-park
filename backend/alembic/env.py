"""Alembic environment.

Safety: every migration run goes through the same guards as the application.
* The final URL (from alembic.ini, ``-c`` config overrides, or DATABASE_URL) is validated before anything else,
  including offline ``--sql`` mode.
* Online runs connect only through ``app.db.session.make_engine``, which re-checks the URL and verifies the actual
  connected database name on every new connection.
* Passing an external connection via ``config.attributes["connection"]`` is refused, so the guards cannot be bypassed.
"""
from __future__ import annotations

from logging.config import fileConfig

from sqlalchemy import pool

import app.models  # noqa: F401 - register models
from alembic import context
from app.core.config import get_settings
from app.core.db_safety import DatabaseSafetyError, validate_database_url
from app.db.base import Base
from app.db.session import make_engine

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata

if config.attributes.get("connection") is not None:
    raise DatabaseSafetyError(
        "Externally supplied Alembic connections are not accepted; configure sqlalchemy.url instead."
    )

settings = get_settings()
# Only the explicit application opt-in (VSP_ALLOW_DATABASE) widens the approved names; protected names never pass.
_EXTRA_ALLOWED = [settings.vsp_allow_database]
_URL = config.get_main_option("sqlalchemy.url") or settings.database_url
# Validate before any mode runs (raises DatabaseSafetyError without exposing the password).
validate_database_url(_URL, extra_allowed=_EXTRA_ALLOWED)


def run_migrations_offline() -> None:
    context.configure(url=_URL, target_metadata=target_metadata, literal_binds=True, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = make_engine(_URL, extra_allowed=_EXTRA_ALLOWED, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
