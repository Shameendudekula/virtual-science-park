from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.db_safety import DatabaseSafetyError, validate_database_url, verify_dbapi_connection

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


_FROM_SETTINGS: Any = object()


def make_engine(
    url: str,
    *,
    extra_allowed: Iterable[str] | None = None,
    expected_port: int | None = _FROM_SETTINGS,
    expected_system_identifier: str | None = _FROM_SETTINGS,
    **kwargs: Any,
) -> Engine:
    """The only way this codebase creates database engines (application, Alembic, entrypoint, tests).

    1. The URL is validated before any engine exists (approved database name, never a protected one).
    2. Every new DBAPI connection verifies the *actual* database name before it can be used, and, when
       configured, the server port and system identifier (VSP_EXPECT_SERVER_PORT / VSP_EXPECT_SYSTEM_IDENTIFIER).
       Pass ``None`` explicitly to skip an identity check; omit the argument to use the settings.
    All timestamps are exchanged in UTC regardless of the server/machine timezone.
    """
    allowed = list(extra_allowed) if extra_allowed is not None else [get_settings().vsp_allow_database]
    if expected_port is _FROM_SETTINGS:
        expected_port = get_settings().expected_server_port
    if expected_system_identifier is _FROM_SETTINGS:
        expected_system_identifier = get_settings().expected_system_identifier
    parsed = validate_database_url(url, extra_allowed=allowed)
    expected = parsed.database
    if not expected:  # unreachable: validate_database_url requires an explicit database name
        raise DatabaseSafetyError("Database URL does not name a database.")
    engine = create_engine(parsed, pool_pre_ping=True, connect_args={"options": "-c timezone=UTC"}, **kwargs)

    @event.listens_for(engine, "connect")
    def _verify_database(dbapi_connection: Any, _record: Any) -> None:
        verify_dbapi_connection(
            dbapi_connection, expected, expected_port=expected_port,
            expected_system_identifier=expected_system_identifier,
        )

    return engine


def get_engine() -> Engine:
    global _engine, _SessionLocal
    if _engine is None:
        _engine = make_engine(get_settings().database_url)
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)
    return _engine


def set_engine(engine: Engine) -> None:
    """Used by tests to point the app at a test database (the engine must come from make_engine)."""
    global _engine, _SessionLocal
    _engine = engine
    _SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def SessionLocal() -> Session:  # noqa: N802 - factory-style name
    get_engine()
    assert _SessionLocal is not None
    return _SessionLocal()


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
