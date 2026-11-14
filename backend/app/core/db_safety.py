"""Database safety guards.

These guards protect databases that belong to other projects on the same PostgreSQL server
(in particular the earlier prototype's ``vsp`` and ``vsp_test``) and system databases.

Rules
-----
* Built-in safe names: ``vsp_park`` (application) and ``vsp_park_test`` (tests).
* Any other database name requires a deliberate opt-in (``VSP_ALLOW_DATABASE`` for the
  application, ``VSP_ALLOW_TEST_DATABASE`` for tests). An opt-in can never allow a protected name.
* The URL must name its database explicitly. Without one, libpq falls back to the user name
  (``vsp``), i.e. the protected database, so a missing name is refused.
* After every new connection the *actual* database name (``SELECT current_database()``) must match
  the database the URL names. This catches aliases (poolers, service files, ``PGDATABASE``).
* Optional server identity: when an expected port and/or system identifier is configured, every new
  connection must also report exactly that ``inet_server_port()`` and ``pg_control_system().system_identifier``.
  A NULL port (Unix-socket connection) or any failure to read the identity is refused (fail closed).
* Tripwire (armed by the test suite): every ``DatabaseSafetyError`` is recorded, even if some code catches
  it. Once tripped, all further connections are refused and the test suite aborts the session.

This module has no dependency on application settings so that tests and tooling can use it before
anything else is configured. Error messages never contain passwords or other secret values.
"""
from __future__ import annotations

import contextlib
import re
from collections.abc import Iterable, Iterator
from typing import Any

from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError

PROTECTED_DATABASES = frozenset({"vsp", "vsp_test", "postgres", "template0", "template1"})
SAFE_APP_DATABASES = frozenset({"vsp_park", "vsp_park_test"})
SAFE_TEST_DATABASE = "vsp_park_test"
ALLOWED_DRIVERS = frozenset({"postgresql", "postgresql+psycopg"})
FORBIDDEN_QUERY_KEYS = frozenset({"service", "dbname", "database"})
_NAME_RE = re.compile(r"^[A-Za-z0-9_]{1,63}$")
_SYSTEM_ID_RE = re.compile(r"^[0-9]{1,20}$")


class _Tripwire:
    """Process-wide record of safety violations. Inert until armed (the test suite arms it)."""

    def __init__(self) -> None:
        self.armed = False
        self.suspended = 0
        self.violations: list[str] = []

    def record(self, message: str) -> None:
        if self.armed and not self.suspended:
            self.violations.append(message)

    @property
    def tripped(self) -> bool:
        return bool(self.violations)


TRIPWIRE = _Tripwire()


def arm_tripwire() -> None:
    TRIPWIRE.armed = True


@contextlib.contextmanager
def tripwire_suspended() -> Iterator[None]:
    """For unit tests that raise safety errors on purpose (fake connections only, never a real server)."""
    TRIPWIRE.suspended += 1
    try:
        yield
    finally:
        TRIPWIRE.suspended -= 1


class DatabaseSafetyError(RuntimeError):
    """A database URL or connection failed a safety check. The message never contains secrets.

    Construction records the violation on the armed tripwire, so catching the exception cannot hide it.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        TRIPWIRE.record(message)


def redact(url: str | URL) -> str:
    """Render a URL for messages with the password hidden. Unparseable input is not echoed."""
    try:
        parsed = url if isinstance(url, URL) else make_url(url)
    except (ArgumentError, ValueError, TypeError):
        return "<unparseable database URL>"
    return parsed.render_as_string(hide_password=True)


def _check_opt_in(name: str, *, kind: str, must_end_with_test: bool = False) -> str:
    name = name.strip()
    if not _NAME_RE.fullmatch(name):
        raise DatabaseSafetyError(f"{kind} opt-in database name is invalid (letters, digits and underscore only).")
    if name.lower() in PROTECTED_DATABASES:
        raise DatabaseSafetyError(f"{kind} opt-in cannot allow the protected database '{name}'.")
    if must_end_with_test and not name.lower().endswith("_test"):
        raise DatabaseSafetyError(f"{kind} opt-in database name must end with '_test'.")
    return name


def parse_and_check(url: str | URL) -> URL:
    """Structural checks shared by application and test URLs. Returns the parsed URL."""
    try:
        parsed = url if isinstance(url, URL) else make_url(str(url))
    except (ArgumentError, ValueError, TypeError):
        raise DatabaseSafetyError("Database URL could not be parsed.") from None
    shown = redact(parsed)
    if parsed.drivername not in ALLOWED_DRIVERS:
        raise DatabaseSafetyError(
            f"Database driver '{parsed.drivername}' is not allowed ({shown}). Use postgresql+psycopg."
        )
    forbidden = sorted(k for k in parsed.query if k.lower() in FORBIDDEN_QUERY_KEYS)
    if forbidden:
        raise DatabaseSafetyError(
            f"Database URL must not select the database via query parameters {forbidden} ({shown})."
        )
    if not parsed.database:
        raise DatabaseSafetyError(
            f"Database URL does not name a database ({shown}). Without one, PostgreSQL connects to a database named "
            "after the user, which may be a protected database."
        )
    if parsed.database.lower() in PROTECTED_DATABASES:
        raise DatabaseSafetyError(f"Refusing to use the protected database '{parsed.database}' ({shown}).")
    return parsed


def validate_database_url(url: str | URL, extra_allowed: Iterable[str] = ()) -> URL:
    """Validate an application database URL. Allowed: vsp_park, vsp_park_test, or explicit opt-ins."""
    parsed = parse_and_check(url)
    allowed = set(SAFE_APP_DATABASES)
    for name in extra_allowed:
        if name and name.strip():
            allowed.add(_check_opt_in(name, kind="VSP_ALLOW_DATABASE"))
    if parsed.database not in allowed:
        raise DatabaseSafetyError(
            f"Database '{parsed.database}' is not an approved database ({redact(parsed)}). Use vsp_park, or set "
            f"VSP_ALLOW_DATABASE={parsed.database} to opt in deliberately."
        )
    return parsed


def validate_test_database_url(url: str | URL, opt_in: str = "") -> URL:
    """Validate the URL of a database the test suite may wipe. Allowed: vsp_park_test or an explicit *_test opt-in."""
    parsed = parse_and_check(url)
    allowed = {SAFE_TEST_DATABASE}
    if opt_in and opt_in.strip():
        allowed.add(_check_opt_in(opt_in, kind="VSP_ALLOW_TEST_DATABASE", must_end_with_test=True))
    if parsed.database not in allowed:
        raise DatabaseSafetyError(
            f"Test database '{parsed.database}' is not approved ({redact(parsed)}). The test suite drops and recreates "
            f"the public schema, so it only runs against {SAFE_TEST_DATABASE} or a database named in "
            "VSP_ALLOW_TEST_DATABASE."
        )
    return parsed


def check_connected_database(actual: str | None, expected: str) -> None:
    """Compare the name reported by the server with the name the URL requested."""
    if not actual:
        raise DatabaseSafetyError("Connected database did not report its name; refusing to continue.")
    if actual.lower() in PROTECTED_DATABASES:
        raise DatabaseSafetyError(f"Connected to the protected database '{actual}'; refusing to continue.")
    if actual != expected:
        raise DatabaseSafetyError(
            f"Connected to database '{actual}' but '{expected}' was requested; refusing to continue."
        )


def parse_expected_port(value: str | int | None, *, name: str) -> int | None:
    """Parse an expected server port setting. Empty means "not checked"."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    text = str(value).strip()
    if not text.isdigit() or not 1 <= int(text) <= 65535:
        raise DatabaseSafetyError(f"{name} must be a port number between 1 and 65535.")
    return int(text)


def parse_expected_system_identifier(value: str | int | None, *, name: str) -> str | None:
    """Parse an expected PostgreSQL system identifier (decimal digits). Empty means "not checked"."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    text = str(value).strip()
    if not _SYSTEM_ID_RE.fullmatch(text):
        raise DatabaseSafetyError(f"{name} must be the numeric database system identifier.")
    return text


def identity_query(*, include_system_identifier: bool) -> str:
    """SQL returning (database, port, system identifier). The system identifier is only read when checked."""
    system_id = "(SELECT system_identifier::text FROM pg_control_system())" if include_system_identifier else "NULL"
    return f"SELECT current_database(), inet_server_port(), {system_id}"


def check_server_identity(
    actual_database: str | None,
    actual_port: int | str | None,
    actual_system_identifier: str | int | None,
    *,
    expected_database: str,
    expected_port: int | None = None,
    expected_system_identifier: str | None = None,
) -> None:
    """Compare what the server reports with what is expected. Missing (NULL) values are refused."""
    check_connected_database(actual_database, expected_database)
    if expected_port is not None:
        if actual_port is None:
            raise DatabaseSafetyError(
                "Server did not report its port (NULL: not a TCP connection); refusing to continue."
            )
        if str(actual_port) != str(expected_port):
            raise DatabaseSafetyError(
                f"Connected to server port {actual_port} but {expected_port} was expected; refusing to continue."
            )
    if expected_system_identifier is not None:
        if actual_system_identifier is None or not str(actual_system_identifier).strip():
            raise DatabaseSafetyError("Server did not report its system identifier; refusing to continue.")
        if str(actual_system_identifier).strip() != expected_system_identifier:
            raise DatabaseSafetyError(
                "Connected to a server with a different system identifier than expected; refusing to continue."
            )


def verify_dbapi_connection(
    dbapi_connection: Any,
    expected: str,
    *,
    expected_port: int | None = None,
    expected_system_identifier: str | None = None,
) -> None:
    """SQLAlchemy 'connect' hook body: verify a fresh DBAPI connection before it can be used.

    Always checks the database name; also checks the server port and system identifier when expected.
    Runs in autocommit mode so no transaction is left open, restores the previous mode, and closes the
    connection before raising so it never reaches the pool. Fails closed: if an identity check is
    configured and the identity cannot be read (e.g. insufficient privilege), the connection is refused.
    Once the tripwire has recorded a violation, every connection is refused.
    """
    identity_required = expected_port is not None or expected_system_identifier is not None
    previous = getattr(dbapi_connection, "autocommit", None)
    try:
        if TRIPWIRE.tripped:
            raise DatabaseSafetyError("A database safety violation was recorded earlier; refusing all connections.")
        try:
            if previous is not None:
                dbapi_connection.autocommit = True
            cursor = dbapi_connection.cursor()
            try:
                if identity_required:
                    cursor.execute(identity_query(include_system_identifier=expected_system_identifier is not None))
                else:
                    cursor.execute("SELECT current_database()")
                row = cursor.fetchone()
            finally:
                cursor.close()
            if previous is not None:
                dbapi_connection.autocommit = previous
        except DatabaseSafetyError:
            raise
        except Exception as exc:
            if not identity_required:
                raise
            raise DatabaseSafetyError(
                f"Could not verify the server identity ({type(exc).__name__}); refusing to continue."
            ) from None
        if identity_required:
            database, port, system_id = (tuple(row) + (None, None, None))[:3] if row else (None, None, None)
            check_server_identity(
                database, port, system_id, expected_database=expected,
                expected_port=expected_port, expected_system_identifier=expected_system_identifier,
            )
        else:
            check_connected_database(row[0] if row else None, expected)
    except DatabaseSafetyError:
        with contextlib.suppress(Exception):
            dbapi_connection.close()
        raise
