"""Test fixtures. Tests run against a real PostgreSQL test database built with the Alembic migrations.

Database safety, in execution order:
1. At import, before any engine exists: TEST_DATABASE_URL must name ``vsp_park_test`` or the database named in
   ``VSP_ALLOW_TEST_DATABASE`` (must end with ``_test``; never a protected database such as ``vsp``/``vsp_test``).
   Database-backed runs also require ``VSP_TEST_EXPECTED_PORT`` (equal to the port stated in the URL) and accept
   ``VSP_TEST_EXPECTED_SYSTEM_ID``. Any failure aborts the session with exit code 4 before anything connects.
2. Every new connection (application, fixtures and Alembic) verifies ``current_database()``, ``inet_server_port()``
   and, when given, the server system identifier (``make_engine`` connect hook).
3. ``recreate_schema`` re-checks the same identity inside the transaction that runs ``DROP SCHEMA``, immediately
   before it.
4. Tripwire: every ``DatabaseSafetyError`` is recorded even if a test or fixture catches it. A tripped tripwire
   refuses all further connections and aborts the whole session after the current test phase (exit code 4).

``VSP_TEST_NO_DB=1`` runs only database-independent tests: every database fixture is skipped and the test URL is
redirected to a closed local port, so an accidental connection fails instead of reaching PostgreSQL.

The reference date is pinned to the date the bundled source snapshots were collected, so deadline-based
assertions are reproducible regardless of when the suite runs.
"""
from __future__ import annotations

import os

import pytest

from app.core.db_safety import (
    TRIPWIRE,
    DatabaseSafetyError,
    arm_tripwire,
    check_server_identity,
    identity_query,
    parse_expected_port,
    parse_expected_system_identifier,
    redact,
    validate_test_database_url,
)

DEFAULT_TEST_DATABASE_URL = "postgresql+psycopg://vsp:vsp@localhost:5432/vsp_park_test"
NO_DB = os.environ.get("VSP_TEST_NO_DB") == "1"
NO_DB_REASON = "database tests disabled (VSP_TEST_NO_DB=1)"
SAFETY_EXIT_CODE = 4

arm_tripwire()


def _abort(message: str) -> None:
    pytest.exit(f"{message} Aborting the whole test session.", returncode=SAFETY_EXIT_CODE)


# ---- guard 1: validate the test database URL and expected server identity before anything else -----------------
_opt_in = os.environ.get("VSP_ALLOW_TEST_DATABASE", "")
EXPECTED_PORT: int | None = None
EXPECTED_SYSTEM_ID: str | None = None
try:
    _test_url = validate_test_database_url(
        os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL), opt_in=_opt_in
    )
    if not NO_DB:
        EXPECTED_PORT = parse_expected_port(os.environ.get("VSP_TEST_EXPECTED_PORT", ""), name="VSP_TEST_EXPECTED_PORT")
        EXPECTED_SYSTEM_ID = parse_expected_system_identifier(
            os.environ.get("VSP_TEST_EXPECTED_SYSTEM_ID", ""), name="VSP_TEST_EXPECTED_SYSTEM_ID"
        )
        if EXPECTED_PORT is None:
            raise DatabaseSafetyError(
                "VSP_TEST_EXPECTED_PORT is required for database-backed tests (the port of the test server)."
            )
        if _test_url.port != EXPECTED_PORT:
            raise DatabaseSafetyError(
                "TEST_DATABASE_URL must state its port explicitly and it must equal VSP_TEST_EXPECTED_PORT."
            )
except DatabaseSafetyError as exc:
    pytest.exit(f"Refusing to run the test suite: {exc}", returncode=SAFETY_EXIT_CODE)

_database_name = _test_url.database
if not _database_name:  # unreachable: the URL validation requires an explicit database name
    pytest.exit("Refusing to run the test suite: TEST_DATABASE_URL names no database.", returncode=SAFETY_EXIT_CODE)
TEST_DATABASE_NAME: str = _database_name
if NO_DB:
    # A closed local port: any accidental connection fails immediately and never reaches a real server.
    _test_url = _test_url.set(host="127.0.0.1", port=9)
TEST_DATABASE_URL = _test_url.render_as_string(hide_password=False)

os.environ["TEST_DATABASE_URL"] = TEST_DATABASE_URL
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
if TEST_DATABASE_NAME != "vsp_park_test":
    os.environ["VSP_ALLOW_DATABASE"] = TEST_DATABASE_NAME  # the validated *_test opt-in, for app settings and Alembic
# The same identity is enforced on every connection made by the app and by Alembic (via make_engine + settings).
os.environ["VSP_EXPECT_SERVER_PORT"] = "" if EXPECTED_PORT is None else str(EXPECTED_PORT)
os.environ["VSP_EXPECT_SYSTEM_IDENTIFIER"] = EXPECTED_SYSTEM_ID or ""
os.environ["REFERENCE_DATE"] = "2026-11-13"
os.environ["AUTO_SEED"] = "false"
os.environ["ADMIN_TOKEN"] = "test-admin-token"
os.environ["DEMO_MODE"] = "true"
os.environ["LLM_PROVIDER"] = "none"
os.environ["LLM_API_KEY"] = ""
os.environ["ENVIRONMENT"] = "test"

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select, text  # noqa: E402

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.db.session import SessionLocal, make_engine, set_engine  # noqa: E402

get_settings.cache_clear()
ENGINE = make_engine(  # lazy: does not connect yet
    TEST_DATABASE_URL, extra_allowed=[TEST_DATABASE_NAME],
    expected_port=EXPECTED_PORT, expected_system_identifier=EXPECTED_SYSTEM_ID,
)
set_engine(ENGINE)
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---- guard 4: the tripwire aborts the session; test code cannot swallow it -------------------------------------
def abort_if_tripped(where: str) -> None:
    if TRIPWIRE.tripped:
        _abort(f"Database safety violation recorded ({where}): {TRIPWIRE.violations[0]}")


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_makereport(item, call):  # noqa: ANN001, ANN201 - pytest hook signature
    # Runs after every setup/call/teardown phase, outside test and fixture code, so nothing can catch the exit.
    abort_if_tripped(f"{item.nodeid}, {call.when}")


def pytest_collection_finish(session):  # noqa: ANN001, ANN201 - pytest hook signature
    abort_if_tripped("collection")


def pytest_sessionfinish(session, exitstatus):  # noqa: ANN001, ANN201 - pytest hook signature
    if TRIPWIRE.tripped:
        session.exitstatus = SAFETY_EXIT_CODE


# ---- guard 3: server identity immediately before destructive SQL ------------------------------------------------
def verify_server_identity(conn) -> None:  # noqa: ANN001 - SQLAlchemy connection
    """Check database name, server port and (when given) system identifier on the connection about to run DDL."""
    abort_if_tripped("before schema reset")
    try:
        row = conn.execute(text(identity_query(include_system_identifier=EXPECTED_SYSTEM_ID is not None))).one()
        check_server_identity(
            *row, expected_database=TEST_DATABASE_NAME, expected_port=EXPECTED_PORT,
            expected_system_identifier=EXPECTED_SYSTEM_ID,
        )
    except DatabaseSafetyError as exc:
        _abort(f"Refusing to reset the schema of {redact(TEST_DATABASE_URL)}: {exc}")
    except Exception as exc:  # e.g. the identity query itself failed: fail closed
        _abort(f"Refusing to reset the schema: server identity could not be verified ({type(exc).__name__}).")


def recreate_schema() -> None:
    if NO_DB:
        pytest.skip(NO_DB_REASON)
    try:
        with ENGINE.begin() as conn:  # connect hook (guard 2) runs first on a new connection
            verify_server_identity(conn)  # guard 3, same transaction as the DDL below
            conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
        cfg = Config(os.path.join(BACKEND_DIR, "alembic.ini"))
        cfg.set_main_option("script_location", os.path.join(BACKEND_DIR, "alembic"))
        cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL.replace("%", "%%"))
        command.upgrade(cfg, "head")  # Alembic connects via make_engine: guard 2 again, from settings
    except DatabaseSafetyError as exc:
        _abort(f"Database safety check failed during schema reset: {exc}")


@pytest.fixture(scope="module")
def seeded():
    """A fully seeded database (sources, technologies, profiles, snapshots, recomputed intelligence)."""
    from app.seed.loader import seed_all

    recreate_schema()
    db = SessionLocal()
    seed_all(db)
    db.close()
    yield


@pytest.fixture(scope="module")
def bare():
    """Schema + source registry + technologies only (for collector tests)."""
    from app.seed.loader import seed_sources, seed_technologies

    recreate_schema()
    db = SessionLocal()
    seed_sources(db)
    seed_technologies(db)
    db.commit()
    db.close()
    yield


@pytest.fixture
def db():
    if NO_DB:
        pytest.skip(NO_DB_REASON)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def reset_after(seeded):
    yield
    from app.seed.loader import reset_demo

    s = SessionLocal()
    reset_demo(s)
    s.close()


@pytest.fixture
def client(seeded):
    from app.main import app
    from app.security.deps import limiter

    limiter.reset()
    with TestClient(app) as c:
        yield c


def company_id(db, slug: str) -> int:
    from app.models import Company

    return db.scalar(select(Company.id).where(Company.slug == slug))
