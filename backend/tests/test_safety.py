"""Regression tests for the database and configuration safety guards.

Every test here is database-independent: nothing connects to PostgreSQL. Subprocess tests point at a closed local
port (127.0.0.1:9) and use only ``--collect-only``, Alembic's offline ``--sql`` mode, or throwaway test files that
never touch a database. Database connections are simulated with fake DBAPI/SQLAlchemy objects.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core import db_safety
from app.core.config import ConfigurationError, Settings, env_files
from app.core.db_safety import (
    DatabaseSafetyError,
    _Tripwire,
    check_connected_database,
    check_server_identity,
    identity_query,
    parse_expected_port,
    parse_expected_system_identifier,
    redact,
    tripwire_suspended,
    validate_database_url,
    validate_test_database_url,
    verify_dbapi_connection,
)
from app.db.session import make_engine

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = BACKEND_DIR.parent
SECRET = "Sup3rSecretPw"  # must never appear in any error message
CLOSED = "127.0.0.1:9"  # nothing listens here; an accidental connection fails immediately
SYSID = "7311111111111111111"  # example PostgreSQL system identifier
OTHER_SYSID = "7322222222222222222"


@pytest.fixture(autouse=True)
def _expected_violations():
    """These tests raise DatabaseSafetyError on purpose (fake connections only), so the session tripwire that
    conftest arms is suspended here. Tripwire behaviour itself is tested with private instances and subprocesses."""
    with tripwire_suspended():
        yield


def url(db: str | None, password: str = SECRET, driver: str = "postgresql+psycopg", query: str = "") -> str:
    path = f"/{db}" if db is not None else ""
    return f"{driver}://vsp:{password}@{CLOSED}{path}{query}"


def assert_refused(func, *args, match: str, **kwargs) -> str:
    with pytest.raises(DatabaseSafetyError, match=match) as info:
        func(*args, **kwargs)
    message = str(info.value)
    assert SECRET not in message
    return message


# ---------------------------------------------------------------------------------------------- application URLs
@pytest.mark.parametrize("name", ["vsp", "vsp_test", "VSP", "Vsp_Test", "postgres", "template0", "template1"])
def test_protected_databases_are_refused(name):
    assert_refused(validate_database_url, url(name), match="protected")


@pytest.mark.parametrize("name", ["vsp", "vsp_test", "VSP_TEST", "postgres"])
def test_opt_in_can_never_allow_a_protected_database(name):
    assert_refused(validate_database_url, url(name), extra_allowed=[name], match="protected")


def test_approved_application_databases_pass():
    assert validate_database_url(url("vsp_park")).database == "vsp_park"
    assert validate_database_url(url("vsp_park_test")).database == "vsp_park_test"


def test_other_databases_need_a_deliberate_opt_in():
    assert_refused(validate_database_url, url("my_park"), match="not an approved database")
    assert validate_database_url(url("my_park"), extra_allowed=["my_park"]).database == "my_park"
    assert_refused(validate_database_url, url("my_park"), extra_allowed=["other"], match="not an approved database")


@pytest.mark.parametrize("bad", ["my-park", "park;drop", "a" * 64, "x y"])
def test_malformed_opt_in_names_are_refused(bad):
    assert_refused(validate_database_url, url("vsp_park"), extra_allowed=[bad], match="invalid")


def test_missing_database_name_is_refused():
    # libpq would fall back to the user name ("vsp"), i.e. the protected database.
    assert_refused(validate_database_url, url(None), match="does not name a database")
    assert_refused(validate_database_url, url(""), match="does not name a database")


@pytest.mark.parametrize("query", ["?service=prod", "?dbname=vsp", "?database=vsp", "?DBNAME=vsp"])
def test_database_selection_via_query_parameters_is_refused(query):
    assert_refused(validate_database_url, url("vsp_park", query=query), match="query parameters")


@pytest.mark.parametrize("driver", ["sqlite", "mysql+pymysql", "postgresql+asyncpg"])
def test_other_drivers_are_refused(driver):
    assert_refused(validate_database_url, url("vsp_park", driver=driver), match="not allowed")


def test_unparseable_url_is_not_echoed():
    message = assert_refused(validate_database_url, f"not a url {SECRET}", match="could not be parsed")
    assert redact(f"::{SECRET}::") == "<unparseable database URL>"
    assert "not a url" not in message


def test_redact_hides_password():
    shown = redact(url("vsp_park"))
    assert SECRET not in shown and "***" in shown


# --------------------------------------------------------------------------------------------------- test URLs
def test_test_database_must_be_vsp_park_test():
    assert validate_test_database_url(url("vsp_park_test")).database == "vsp_park_test"
    for name in ("vsp_park", "vsp", "vsp_test", "postgres", "something_test"):
        assert_refused(validate_test_database_url, url(name), match="protected|not approved")


def test_test_opt_in_must_end_with_test_and_never_be_protected():
    assert validate_test_database_url(url("ci_park_test"), opt_in="ci_park_test").database == "ci_park_test"
    assert_refused(validate_test_database_url, url("vsp_park"), opt_in="vsp_park", match="must end with '_test'")
    assert_refused(validate_test_database_url, url("vsp_test"), opt_in="vsp_test", match="protected")
    assert_refused(validate_test_database_url, url("VSP_TEST"), opt_in="VSP_TEST", match="protected")
    assert_refused(validate_test_database_url, url("other_test"), opt_in="ci_park_test", match="not approved")


# ------------------------------------------------------------------------------------- connected-database check
class FakeCursor:
    def __init__(self, conn: FakeConnection):
        self.conn = conn

    def execute(self, sql: str) -> None:
        self.conn.executed.append((sql, self.conn.autocommit))
        if self.conn.fail_with is not None:
            raise self.conn.fail_with
        self.identity = "inet_server_port" in sql

    def fetchone(self):
        if self.conn.no_row:
            return None
        if self.identity:  # the identity query returns NULL for the system identifier unless it was requested
            sysid = self.conn.sysid if "pg_control_system" in self.conn.executed[-1][0] else None
            return (self.conn.reported, self.conn.port, sysid)
        return None if self.conn.reported is None else (self.conn.reported,)

    def close(self) -> None:
        pass


class FakeConnection:
    def __init__(self, reported: str | None, port: int | None = None, sysid: str | None = None,
                 fail_with: Exception | None = None, no_row: bool = False):
        self.reported = reported
        self.port = port
        self.sysid = sysid
        self.fail_with = fail_with
        self.no_row = no_row
        self.autocommit = False
        self.closed = False
        self.executed: list[tuple[str, bool]] = []

    def cursor(self) -> FakeCursor:
        return FakeCursor(self)

    def close(self) -> None:
        self.closed = True


def test_connection_check_passes_and_restores_autocommit():
    conn = FakeConnection("vsp_park")
    verify_dbapi_connection(conn, "vsp_park")
    assert conn.executed == [("SELECT current_database()", True)]  # ran in autocommit: no open transaction
    assert conn.autocommit is False and not conn.closed


@pytest.mark.parametrize("reported,match", [
    ("vsp", "protected"),
    ("vsp_test", "protected"),
    ("postgres", "protected"),
    ("other_db", "was requested"),
    (None, "did not report"),
])
def test_connection_to_wrong_database_is_closed_and_refused(reported, match):
    conn = FakeConnection(reported)
    with pytest.raises(DatabaseSafetyError, match=match):
        verify_dbapi_connection(conn, "vsp_park")
    assert conn.closed  # never handed to the pool


def test_check_connected_database_requires_exact_match():
    check_connected_database("vsp_park_test", "vsp_park_test")
    with pytest.raises(DatabaseSafetyError):
        check_connected_database("VSP_PARK_TEST", "vsp_park_test")


# ----------------------------------------------------------------------------------------------------- engines
def test_make_engine_refuses_protected_database_before_creating_an_engine(monkeypatch):
    created = []
    monkeypatch.setattr("app.db.session.create_engine", lambda *a, **k: created.append(a))
    for name in ("vsp", "vsp_test"):
        assert_refused(make_engine, url(name), extra_allowed=[], match="protected")
        assert_refused(make_engine, url(name), extra_allowed=[name], match="protected")
    assert_refused(make_engine, url(None), extra_allowed=[], match="does not name a database")
    assert created == []


def _verify_listener(engine):
    listeners = [fn for fn in engine.pool.dispatch.connect if getattr(fn, "__name__", "") == "_verify_database"]
    assert len(listeners) == 1, "no connect-time database verification registered"
    return listeners[0]


def test_make_engine_verifies_every_new_connection():
    # lazy: creating the engine does not connect. Identity checks explicitly off: database name only.
    engine = make_engine(url("vsp_park"), extra_allowed=[], expected_port=None, expected_system_identifier=None)
    try:
        listener = _verify_listener(engine)
        good, bad = FakeConnection("vsp_park"), FakeConnection("vsp")
        listener(good, None)
        with pytest.raises(DatabaseSafetyError, match="protected"):
            listener(bad, None)
        assert bad.closed and not good.closed
    finally:
        engine.dispose()


def test_make_engine_verifies_server_identity_on_every_connection():
    engine = make_engine(url("vsp_park"), extra_allowed=[], expected_port=55432, expected_system_identifier=SYSID)
    try:
        listener = _verify_listener(engine)
        good = FakeConnection("vsp_park", 55432, SYSID)
        listener(good, None)
        assert not good.closed
        for bad in (FakeConnection("vsp_park", 5432, SYSID), FakeConnection("vsp_park", None, SYSID),
                    FakeConnection("vsp_park", 55432, OTHER_SYSID), FakeConnection("vsp_park", 55432, None)):
            with pytest.raises(DatabaseSafetyError):
                listener(bad, None)
            assert bad.closed
    finally:
        engine.dispose()


def test_make_engine_takes_server_identity_from_settings(monkeypatch):
    configured = Settings(_env_file=None, database_url=url("vsp_park"), vsp_expect_server_port="55432",
                          vsp_expect_system_identifier=SYSID)
    monkeypatch.setattr("app.db.session.get_settings", lambda: configured)
    engine = make_engine(url("vsp_park"), extra_allowed=[])  # identity arguments omitted -> from settings
    try:
        with pytest.raises(DatabaseSafetyError, match="port 5432 but 55432"):
            _verify_listener(engine)(FakeConnection("vsp_park", 5432, SYSID), None)
        _verify_listener(engine)(FakeConnection("vsp_park", 55432, SYSID), None)
    finally:
        engine.dispose()
    off = make_engine(url("vsp_park"), extra_allowed=[], expected_port=None, expected_system_identifier=None)
    try:
        conn = FakeConnection("vsp_park")
        _verify_listener(off)(conn, None)  # explicit None overrides the settings
        assert conn.executed == [("SELECT current_database()", True)]
    finally:
        off.dispose()


def test_alembic_uses_identity_from_settings():
    # env.py must not override the identity arguments, so the settings (exported by conftest) apply to migrations.
    source = (BACKEND_DIR / "alembic" / "env.py").read_text(encoding="utf-8")
    assert "make_engine(_URL" in source
    assert "expected_port" not in source and "expected_system_identifier" not in source


def test_only_make_engine_creates_engines():
    offenders = []
    for path in [*BACKEND_DIR.joinpath("app").rglob("*.py"), *BACKEND_DIR.joinpath("alembic").rglob("*.py"),
                 BACKEND_DIR / "docker-entrypoint.sh", *BACKEND_DIR.joinpath("scripts").rglob("*.py")]:
        text = path.read_text(encoding="utf-8")
        if path.name == "session.py" and path.parent.name == "db":
            continue
        if re.search(r"\bcreate_engine\s*\(|psycopg\.connect\s*\(", text):
            offenders.append(str(path.relative_to(BACKEND_DIR)))
    assert offenders == []
    assert "make_engine(" in (BACKEND_DIR / "docker-entrypoint.sh").read_text(encoding="utf-8")


# ------------------------------------------------------------------------------------------------------ settings
SETTINGS_ENV = [name.upper() for name in Settings.model_fields]


@pytest.fixture
def clean_env(monkeypatch):
    """No environment variables and no .env files: only explicit keyword arguments count."""
    for name in SETTINGS_ENV:
        monkeypatch.delenv(name, raising=False)
    return lambda **kw: Settings(_env_file=None, **kw)


STRONG_SECRET = "s" * 40
PROD_DB = f"postgresql+psycopg://vsp_app:{SECRET}@db.internal:5432/vsp_park"


def production(**overrides):
    values = dict(environment="production", demo_mode=False, secret_key=STRONG_SECRET, admin_token="",
                  demo_company_password="", database_url=PROD_DB, cors_origins="https://park.example.test")
    values.update(overrides)
    return values


def test_safe_defaults(clean_env):
    s = clean_env()
    assert s.demo_mode is False
    assert s.environment == "development"
    assert s.database_url.endswith("/vsp_park")
    assert s.vsp_allow_database == ""


def test_database_url_is_not_in_repr(clean_env):
    s = clean_env(database_url=url("vsp_park"))
    assert SECRET not in repr(s) and SECRET not in str(s)


@pytest.mark.parametrize("name", ["vsp", "vsp_test", None])
def test_settings_refuse_unsafe_database_without_echoing_secrets(clean_env, name):
    with pytest.raises(ConfigurationError, match="DATABASE_URL rejected") as info:
        clean_env(database_url=url(name))
    assert not isinstance(info.value, ValidationError)  # not wrapped: pydantic would echo the input value
    assert SECRET not in str(info.value)


def test_settings_opt_in_is_explicit_and_cannot_unlock_protected(clean_env):
    assert clean_env(database_url=url("my_park"), vsp_allow_database="my_park").database_url.endswith("/my_park")
    with pytest.raises(ConfigurationError):
        clean_env(database_url=url("my_park"))
    with pytest.raises(ConfigurationError, match="protected"):
        clean_env(database_url=url("vsp"), vsp_allow_database="vsp")


def test_settings_read_database_settings_from_environment(clean_env, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", url("vsp_test"))
    with pytest.raises(ConfigurationError, match="protected") as info:
        Settings(_env_file=None)
    assert SECRET not in str(info.value)


def test_valid_production_configuration_starts(clean_env):
    s = clean_env(**production())
    assert s.production_problems() == []


@pytest.mark.parametrize("overrides,problem", [
    ({"demo_mode": True}, "DEMO_MODE"),
    ({"secret_key": ""}, "SECRET_KEY must be set"),
    ({"secret_key": "short-but-real"}, "SECRET_KEY must be at least 32"),
    ({"secret_key": "change-me-to-a-long-random-string-xxxxxxxx"}, "SECRET_KEY must be at least 32"),
    ({"admin_token": "change-me-admin-token-xxxxxxxx"}, "ADMIN_TOKEN"),
    ({"admin_token": "tooshort"}, "ADMIN_TOKEN"),
    ({"demo_company_password": "change-me-demo-password"}, "DEMO_COMPANY_PASSWORD"),
    ({"demo_company_password": "short"}, "DEMO_COMPANY_PASSWORD"),
    ({"cors_origins": "*"}, "CORS_ORIGINS"),
    ({"database_url": "postgresql+psycopg://vsp:vsp@db:5432/vsp_park"}, "development credentials"),
])
def test_production_refuses_unsafe_configuration(clean_env, overrides, problem):
    with pytest.raises(ConfigurationError, match="Refusing to start in production") as info:
        clean_env(**production(**overrides))
    message = str(info.value)
    assert problem in message
    for value in overrides.values():
        if isinstance(value, str) and len(value) > 1 and value != "*":
            assert value not in message, "a setting value leaked into the error message"
    assert SECRET not in message


def test_development_allows_demo_but_warns_by_name_only(clean_env):
    s = clean_env(demo_mode=True, secret_key="change-me-dev-secret", admin_token="change-me-admin-token")
    warnings = " ".join(s.security_warnings())
    assert "DEMO_MODE" in warnings and "SECRET_KEY" in warnings and "ADMIN_TOKEN" in warnings
    assert "change-me-dev-secret" not in warnings and "change-me-admin-token" not in warnings
    assert clean_env(demo_mode=False, secret_key=STRONG_SECRET).security_warnings() == []


def test_startup_logs_security_warnings(monkeypatch, caplog):
    import app.main as main

    monkeypatch.setattr(main, "_startup", lambda: None)
    monkeypatch.setattr(main, "configure_logging", lambda level: None)

    async def run():
        async with main.lifespan(main.app):
            pass

    with caplog.at_level(logging.WARNING, logger="vsp.api"):
        asyncio.run(run())
    assert any("DEMO_MODE" in r.getMessage() for r in caplog.records)  # the test settings run in demo mode


# ------------------------------------------------------------------------------------------------- .env loading
def test_env_files_are_absolute_and_inside_the_repository():
    files = Settings.model_config["env_file"]
    assert tuple(files) == env_files()
    assert files[0] == BACKEND_DIR / ".env" and files[-1] == REPO_DIR / ".env"
    for f in files:
        assert Path(f).is_absolute()
        assert Path(f).resolve().is_relative_to(REPO_DIR.resolve())


def test_repository_root_env_requires_the_expected_layout(tmp_path):
    (tmp_path / "repo" / "backend").mkdir(parents=True)
    repo = tmp_path / "repo"
    assert env_files(repo / "backend") == (repo / "backend" / ".env", repo / ".env")
    (tmp_path / "app").mkdir()  # container layout: backend copied to /app, the parent is not consulted
    assert env_files(tmp_path / "app") == (tmp_path / "app" / ".env",)


def test_env_file_in_current_directory_is_ignored(tmp_path, monkeypatch, clean_env):
    repo = tmp_path / "repo"
    (repo / "backend").mkdir(parents=True)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / ".env").write_text(f"DATABASE_URL={url('vsp')}\nDEMO_MODE=true\n", encoding="utf-8")
    monkeypatch.chdir(elsewhere)
    s = Settings(_env_file=env_files(repo / "backend"))  # same mechanism as the real model_config
    assert s.demo_mode is False and s.database_url.endswith("/vsp_park")


def test_repository_env_file_is_read(tmp_path, clean_env):
    repo = tmp_path / "repo"
    (repo / "backend").mkdir(parents=True)
    (repo / ".env").write_text("DEMO_MODE=true\n", encoding="utf-8")
    assert Settings(_env_file=env_files(repo / "backend")).demo_mode is True  # explicit local demo still works


# -------------------------------------------------------------------------------------------- test-suite guard
def _subprocess_env(**overrides: str) -> dict[str, str]:
    drop = set(SETTINGS_ENV) | {"VSP_ALLOW_TEST_DATABASE", "VSP_TEST_EXPECTED_PORT", "VSP_TEST_EXPECTED_SYSTEM_ID"}
    env = {k: v for k, v in os.environ.items() if k.upper() not in drop}
    env.update(PYTHONDONTWRITEBYTECODE="1", VSP_TEST_NO_DB="1", ENVIRONMENT="test")
    env.pop("TEST_DATABASE_URL", None)
    env.update(overrides)
    return env


def _collect(**env: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider", "tests/test_matching.py"],
        cwd=BACKEND_DIR, env=_subprocess_env(**env), capture_output=True, text=True, timeout=120,
    )


@pytest.mark.parametrize("name,opt_in", [
    ("vsp", ""), ("vsp_test", ""), ("vsp_park", ""), ("postgres", ""),
    ("vsp_test", "vsp_test"), ("vsp_park", "vsp_park"), (None, ""),
])
def test_suite_refuses_unapproved_test_database(name, opt_in):
    result = _collect(TEST_DATABASE_URL=url(name), VSP_ALLOW_TEST_DATABASE=opt_in)
    output = result.stdout + result.stderr
    assert result.returncode == 4, output
    assert "Refusing to run the test suite" in output
    assert SECRET not in output


def test_suite_accepts_explicit_test_database_opt_in():
    result = _collect(TEST_DATABASE_URL=url("ci_park_test"), VSP_ALLOW_TEST_DATABASE="ci_park_test")
    assert result.returncode == 0, result.stdout + result.stderr


def test_no_db_mode_points_at_a_closed_port():
    import tests.conftest as conftest

    if not conftest.NO_DB:
        pytest.skip("only meaningful with VSP_TEST_NO_DB=1")
    assert "@127.0.0.1:9/" in conftest.TEST_DATABASE_URL


# ---------------------------------------------------------------------------------------------------- Alembic
def _alembic(*args: str, **env: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args], cwd=BACKEND_DIR, env=_subprocess_env(**env),
        capture_output=True, text=True, timeout=120,
    )


@pytest.mark.parametrize("name", ["vsp", "vsp_test", None])
def test_alembic_refuses_protected_database_from_environment(name):
    result = _alembic("upgrade", "head", "--sql", DATABASE_URL=url(name))
    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "protected" in output or "does not name a database" in output
    assert SECRET not in output and "CREATE TABLE" not in output


def _ini_with_url(tmp_path: Path, database_url: str) -> Path:
    ini = (BACKEND_DIR / "alembic.ini").read_text(encoding="utf-8")
    ini = ini.replace("script_location = alembic", f"script_location = {BACKEND_DIR / 'alembic'}", 1)
    ini = ini.replace("[alembic]\n", f"[alembic]\nsqlalchemy.url = {database_url.replace('%', '%%')}\n", 1)
    path = tmp_path / "alembic.ini"
    path.write_text(ini, encoding="utf-8")
    return path


@pytest.mark.parametrize("name", ["vsp", "vsp_test", None])
def test_alembic_refuses_protected_database_from_ini(tmp_path, name):
    ini = _ini_with_url(tmp_path, url(name))
    result = _alembic("-c", str(ini), "upgrade", "head", "--sql", DATABASE_URL=url("vsp_park"))
    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "protected" in output or "does not name a database" in output
    assert SECRET not in output and "CREATE TABLE" not in output


def test_alembic_offline_works_for_approved_database():
    result = _alembic("upgrade", "head", "--sql", DATABASE_URL=url("vsp_park"))
    assert result.returncode == 0, result.stderr[-2000:]
    assert "CREATE TABLE" in result.stdout


def test_alembic_refuses_externally_supplied_connection():
    from alembic import command
    from alembic.config import Config

    cfg = Config()  # no ini file: avoids fileConfig() reconfiguring this process's loggers
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.attributes["connection"] = object()
    with pytest.raises(DatabaseSafetyError, match="Externally supplied"):
        command.upgrade(cfg, "head")


# ------------------------------------------------------------------------------------------ deployment + data
def _compose_ports() -> list[str]:
    ports, collecting = [], False
    for raw in (REPO_DIR / "docker-compose.yml").read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line == "ports:":
            collecting = True
            continue
        if collecting and line.startswith("#"):
            continue
        if collecting and line.startswith("-"):
            ports.append(line.lstrip("- ").strip("\"'"))
            continue
        collecting = False
    return ports


def test_compose_publishes_ports_on_localhost_only():
    ports = _compose_ports()
    assert ports, "no published ports found"
    assert all(p.startswith("127.0.0.1:") for p in ports), ports


RESERVED_EMAIL_DOMAINS = (".test", ".example", ".invalid", ".localhost", "example.com", "example.org", "example.net")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+)")
URL_USERINFO_RE = re.compile(r"[a-z][a-z0-9+.-]*://[^\s/\"'@]*@")


def test_test_fixtures_use_reserved_email_domains_only():
    offenders = []
    for path in BACKEND_DIR.joinpath("tests").rglob("*.py"):
        text = URL_USERINFO_RE.sub("", path.read_text(encoding="utf-8"))  # user:pw@host in URLs is not an email
        for match in EMAIL_RE.finditer(text):
            domain = match.group(1).lower()
            if not domain.endswith(RESERVED_EMAIL_DOMAINS):
                offenders.append(f"{path.name}: {match.group(0)}")
    assert offenders == []


def test_protected_names_cover_the_original_databases():
    assert {"vsp", "vsp_test"} <= db_safety.PROTECTED_DATABASES
    assert not (db_safety.PROTECTED_DATABASES & db_safety.SAFE_APP_DATABASES)


# ============================================================================================ server identity (Gate 1)
ISO_DB = "vsp_park_iso_20261113_test"


@pytest.mark.parametrize("value,expected", [("", None), (None, None), ("  ", None), ("55432", 55432), (" 9 ", 9),
                                            (5432, 5432), ("65535", 65535), ("1", 1)])
def test_parse_expected_port_accepts(value, expected):
    assert parse_expected_port(value, name="X") == expected


@pytest.mark.parametrize("value", ["abc", "0", "65536", "-1", "55432x", "5 432", "1e3"])
def test_parse_expected_port_rejects(value):
    assert_refused(parse_expected_port, value, name="VSP_TEST_EXPECTED_PORT", match="VSP_TEST_EXPECTED_PORT")


@pytest.mark.parametrize("value,expected", [("", None), (None, None), (SYSID, SYSID), (f" {SYSID} ", SYSID)])
def test_parse_expected_system_identifier_accepts(value, expected):
    assert parse_expected_system_identifier(value, name="X") == expected


@pytest.mark.parametrize("value", ["abc", "12-3", "1" * 21, "0x1f", "7311 111"])
def test_parse_expected_system_identifier_rejects(value):
    assert_refused(parse_expected_system_identifier, value, name="SYS", match="numeric")


def test_identity_query_reads_system_identifier_only_when_checked():
    full = identity_query(include_system_identifier=True)
    assert "current_database()" in full and "inet_server_port()" in full and "pg_control_system()" in full
    light = identity_query(include_system_identifier=False)
    assert "inet_server_port()" in light and "pg_control_system" not in light and "NULL" in light


@pytest.mark.parametrize("actual,match", [
    ((ISO_DB, None, SYSID), "did not report its port"),            # NULL port (e.g. Unix socket)
    ((ISO_DB, 5432, SYSID), "port 5432 but 55432"),                # mismatched port
    ((ISO_DB, "5433", SYSID), "port 5433 but 55432"),
    ((ISO_DB, 55432, None), "did not report its system identifier"),  # NULL system identifier
    ((ISO_DB, 55432, ""), "did not report its system identifier"),    # missing system identifier
    ((ISO_DB, 55432, OTHER_SYSID), "different system identifier"),    # mismatched system identifier
    ((None, 55432, SYSID), "did not report its name"),                # NULL database
    (("", 55432, SYSID), "did not report its name"),                  # missing database
    (("other_test", 55432, SYSID), "was requested"),                  # mismatched database
    (("vsp", 55432, SYSID), "protected"),
    (("vsp_park_test", 55432, SYSID), "was requested"),
])
def test_server_identity_mismatches_are_refused(actual, match):
    message = assert_refused(check_server_identity, *actual, expected_database=ISO_DB, expected_port=55432,
                             expected_system_identifier=SYSID, match=match)
    assert SYSID not in message and OTHER_SYSID not in message  # identifiers are not echoed


def test_server_identity_match_passes_and_unconfigured_parts_are_skipped():
    check_server_identity(ISO_DB, 55432, SYSID, expected_database=ISO_DB, expected_port=55432,
                          expected_system_identifier=SYSID)
    check_server_identity(ISO_DB, "55432", int(SYSID), expected_database=ISO_DB, expected_port=55432,
                          expected_system_identifier=SYSID)
    check_server_identity(ISO_DB, None, None, expected_database=ISO_DB)  # nothing but the name configured


def test_identity_connection_check_passes_and_restores_autocommit():
    conn = FakeConnection(ISO_DB, 55432, SYSID)
    verify_dbapi_connection(conn, ISO_DB, expected_port=55432, expected_system_identifier=SYSID)
    assert conn.executed == [(identity_query(include_system_identifier=True), True)]
    assert conn.autocommit is False and not conn.closed


def test_port_only_check_does_not_read_the_system_identifier():
    conn = FakeConnection(ISO_DB, 55432, SYSID)
    verify_dbapi_connection(conn, ISO_DB, expected_port=55432)
    assert conn.executed == [(identity_query(include_system_identifier=False), True)]


@pytest.mark.parametrize("conn,match", [
    (FakeConnection(ISO_DB, None, SYSID), "did not report its port"),
    (FakeConnection(ISO_DB, 5432, SYSID), "port 5432 but 55432"),
    (FakeConnection(ISO_DB, 55432, None), "system identifier"),
    (FakeConnection(ISO_DB, 55432, OTHER_SYSID), "different system identifier"),
    (FakeConnection(None, 55432, SYSID), "did not report its name"),
    (FakeConnection("vsp_test", 55432, SYSID), "protected"),
    (FakeConnection("other_test", 55432, SYSID), "was requested"),
    (FakeConnection(ISO_DB, 55432, SYSID, no_row=True), "did not report its name"),
])
def test_identity_connection_mismatch_is_closed_and_refused(conn, match):
    with pytest.raises(DatabaseSafetyError, match=match):
        verify_dbapi_connection(conn, ISO_DB, expected_port=55432, expected_system_identifier=SYSID)
    assert conn.closed


class InsufficientPrivilege(Exception):
    pass


def test_identity_that_cannot_be_read_fails_closed():
    conn = FakeConnection(ISO_DB, 55432, SYSID, fail_with=InsufficientPrivilege(f"permission denied {SECRET}"))
    expected_message = r"Could not verify the server identity \(InsufficientPrivilege\)"
    with pytest.raises(DatabaseSafetyError, match=expected_message) as e:
        verify_dbapi_connection(conn, ISO_DB, expected_port=55432, expected_system_identifier=SYSID)
    assert conn.closed and SECRET not in str(e.value)


def test_name_only_check_keeps_driver_errors_unchanged():
    conn = FakeConnection("vsp_park", fail_with=InsufficientPrivilege("boom"))
    with pytest.raises(InsufficientPrivilege):
        verify_dbapi_connection(conn, "vsp_park")


def test_settings_validate_expected_identity(clean_env):
    s = clean_env(vsp_expect_server_port="55432", vsp_expect_system_identifier=SYSID)
    assert s.expected_server_port == 55432 and s.expected_system_identifier == SYSID
    assert clean_env().expected_server_port is None and clean_env().expected_system_identifier is None
    for kwargs, name in (({"vsp_expect_server_port": "abc"}, "VSP_EXPECT_SERVER_PORT"),
                         ({"vsp_expect_server_port": "70000"}, "VSP_EXPECT_SERVER_PORT"),
                         ({"vsp_expect_system_identifier": "xyz"}, "VSP_EXPECT_SYSTEM_IDENTIFIER")):
        with pytest.raises(ConfigurationError, match=name) as info:
            clean_env(**kwargs)
        assert not isinstance(info.value, ValidationError)


def test_conftest_exports_the_expected_identity_to_app_and_alembic():
    import tests.conftest as conftest
    from app.core.config import get_settings

    exported = "" if conftest.EXPECTED_PORT is None else str(conftest.EXPECTED_PORT)
    assert os.environ["VSP_EXPECT_SERVER_PORT"] == exported
    assert os.environ["VSP_EXPECT_SYSTEM_IDENTIFIER"] == (conftest.EXPECTED_SYSTEM_ID or "")
    assert get_settings().expected_server_port == conftest.EXPECTED_PORT
    if not conftest.NO_DB:
        assert conftest.EXPECTED_PORT is not None  # database-backed runs always check the port


# ---------------------------------------------------------------------------------------------------- tripwire
def test_tripwire_records_violations_even_when_caught(monkeypatch):
    wire = _Tripwire()
    monkeypatch.setattr(db_safety, "TRIPWIRE", wire)
    DatabaseSafetyError("before arming")
    assert not wire.tripped  # inert in the application
    wire.armed = True
    with tripwire_suspended():
        DatabaseSafetyError("expected in a unit test")
    assert not wire.tripped
    try:
        raise DatabaseSafetyError("swallowed by careless code")
    except Exception:  # noqa: BLE001 - deliberately swallowing
        pass
    assert wire.tripped and wire.violations == ["swallowed by careless code"]


@pytest.mark.parametrize("kwargs", [{}, {"expected_port": 55432, "expected_system_identifier": SYSID}])
def test_tripped_tripwire_refuses_every_connection(monkeypatch, kwargs):
    wire = _Tripwire()
    wire.armed, wire.violations = True, ["earlier violation"]
    monkeypatch.setattr(db_safety, "TRIPWIRE", wire)
    conn = FakeConnection(ISO_DB, 55432, SYSID)  # a perfectly matching connection is still refused
    with pytest.raises(DatabaseSafetyError, match="violation was recorded earlier"):
        verify_dbapi_connection(conn, ISO_DB, **kwargs)
    assert conn.closed and conn.executed == []


# --------------------------------------------------------------- schema reset: identity check precedes every DDL
class FakeResult:
    def __init__(self, row):
        self._row = row

    def one(self):
        return self._row


class FakeSAConnection:
    def __init__(self, row, fail: Exception | None = None):
        self.row, self.fail, self.sql = row, fail, []

    def execute(self, statement):
        sql = str(statement)
        self.sql.append(sql)
        if "current_database()" in sql:
            if self.fail is not None:
                raise self.fail
            return FakeResult(self.row)
        return FakeResult(None)


class FakeEngine:
    def __init__(self, conn: FakeSAConnection):
        self.conn = conn

    @contextlib.contextmanager
    def begin(self):
        yield self.conn


class FakeAlembicCommand:
    def __init__(self, fail: Exception | None = None):
        self.calls, self.fail = 0, fail

    def upgrade(self, cfg, revision):
        self.calls += 1
        if self.fail is not None:
            raise self.fail


@pytest.fixture
def fake_reset(monkeypatch):
    """recreate_schema against a fake engine; returns (conftest, connection, alembic command)."""
    import tests.conftest as conftest

    def build(row, *, fail=None, upgrade_fail=None):
        conn, cmd = FakeSAConnection(row, fail), FakeAlembicCommand(upgrade_fail)
        monkeypatch.setattr(conftest, "NO_DB", False)
        monkeypatch.setattr(conftest, "ENGINE", FakeEngine(conn))
        monkeypatch.setattr(conftest, "EXPECTED_PORT", 55432)
        monkeypatch.setattr(conftest, "EXPECTED_SYSTEM_ID", SYSID)
        monkeypatch.setattr(conftest, "command", cmd)
        return conftest, conn, cmd

    return build


def test_schema_reset_checks_identity_before_drop_create_and_migrations(fake_reset):
    import tests.conftest as conftest

    _, conn, cmd = fake_reset((conftest.TEST_DATABASE_NAME, 55432, SYSID))
    conftest.recreate_schema()
    assert conn.sql[0] == identity_query(include_system_identifier=True)
    assert [q for q in conn.sql[1:]] == ["DROP SCHEMA IF EXISTS public CASCADE", "CREATE SCHEMA public"]
    assert cmd.calls == 1  # migrations only after the identity check passed


@pytest.mark.parametrize("row", [
    ("{db}", None, SYSID), ("{db}", 5432, SYSID), ("{db}", 55432, None), ("{db}", 55432, ""),
    ("{db}", 55432, OTHER_SYSID), (None, 55432, SYSID), ("other_db_test", 55432, SYSID), ("vsp", 55432, SYSID),
])
def test_schema_reset_aborts_session_before_drop_on_identity_mismatch(fake_reset, row):
    import tests.conftest as conftest

    row = tuple(conftest.TEST_DATABASE_NAME if v == "{db}" else v for v in row)
    _, conn, cmd = fake_reset(row)
    with pytest.raises(pytest.exit.Exception, match="Aborting the whole test session") as info:
        conftest.recreate_schema()
    assert info.value.returncode == 4
    assert not any("DROP" in q or "CREATE" in q for q in conn.sql) and cmd.calls == 0


def test_schema_reset_aborts_when_identity_cannot_be_read(fake_reset):
    import tests.conftest as conftest

    _, conn, cmd = fake_reset(None, fail=InsufficientPrivilege(f"permission denied {SECRET}"))
    with pytest.raises(pytest.exit.Exception, match="could not be verified") as info:
        conftest.recreate_schema()
    assert SECRET not in str(info.value)
    assert not any("DROP" in q for q in conn.sql) and cmd.calls == 0


def test_schema_reset_aborts_when_tripwire_already_tripped(fake_reset, monkeypatch):
    import tests.conftest as conftest

    _, conn, cmd = fake_reset((conftest.TEST_DATABASE_NAME, 55432, SYSID))
    wire = _Tripwire()
    wire.armed, wire.violations = True, ["earlier violation"]
    # Scoped patch: undone before this test's report, or the session hook would (correctly) abort the real run.
    with monkeypatch.context() as patch:
        patch.setattr(conftest, "TRIPWIRE", wire)
        with pytest.raises(pytest.exit.Exception, match="earlier violation"):
            conftest.recreate_schema()
    assert conn.sql == [] and cmd.calls == 0


def test_schema_reset_aborts_when_migration_connection_fails_identity(fake_reset):
    import tests.conftest as conftest

    _, _, cmd = fake_reset((conftest.TEST_DATABASE_NAME, 55432, SYSID),
                           upgrade_fail=DatabaseSafetyError("Connected to server port 5432 but 55432 was expected"))
    with pytest.raises(pytest.exit.Exception, match="during schema reset") as info:
        conftest.recreate_schema()
    assert info.value.returncode == 4 and cmd.calls == 1


# ------------------------------------------------------------- conftest: database-backed runs need the identity
def _db_collect(**env: str) -> subprocess.CompletedProcess[str]:
    base = {"VSP_TEST_NO_DB": "0", "TEST_DATABASE_URL": url("ci_park_test"),
            "VSP_ALLOW_TEST_DATABASE": "ci_park_test"}
    return _collect(**{**base, **env})


@pytest.mark.parametrize("env,match", [
    ({}, "VSP_TEST_EXPECTED_PORT is required"),
    ({"VSP_TEST_EXPECTED_PORT": ""}, "VSP_TEST_EXPECTED_PORT is required"),
    ({"VSP_TEST_EXPECTED_PORT": "abc"}, "must be a port number"),
    ({"VSP_TEST_EXPECTED_PORT": "0"}, "must be a port number"),
    ({"VSP_TEST_EXPECTED_PORT": "55432"}, "must state its port explicitly"),  # URL says 9
    ({"VSP_TEST_EXPECTED_PORT": "5432",
      "TEST_DATABASE_URL": f"postgresql+psycopg://vsp:{SECRET}@127.0.0.1/ci_park_test"}, "must state its port"),
    ({"VSP_TEST_EXPECTED_PORT": "9", "VSP_TEST_EXPECTED_SYSTEM_ID": "not-a-number"}, "numeric"),
])
def test_database_runs_refuse_missing_or_mismatched_expected_identity(env, match):
    result = _db_collect(**env)
    output = result.stdout + result.stderr
    assert result.returncode == 4, output
    assert "Refusing to run the test suite" in output and match in output
    assert SECRET not in output


def test_database_runs_accept_a_complete_expected_identity():
    # Collection only: the engine is lazy and port 9 is closed, so nothing connects.
    result = _db_collect(VSP_TEST_EXPECTED_PORT="9", VSP_TEST_EXPECTED_SYSTEM_ID=SYSID)
    assert result.returncode == 0, result.stdout + result.stderr


# ------------------------------------------------- tripwire: the whole session stops, nothing can swallow it
SWALLOW_IN_TEST = """
from app.core.db_safety import DatabaseSafetyError

def test_1_swallows_a_violation():
    try:
        raise DatabaseSafetyError("simulated violation in a test")
    except BaseException:
        pass

def test_2_must_not_run():
    open(MARKER, "w").write("ran")
"""

SWALLOW_IN_FIXTURE = """
import pytest
from app.core.db_safety import DatabaseSafetyError

@pytest.fixture(scope="module")
def careless_fixture():
    try:
        raise DatabaseSafetyError("simulated violation in a fixture")
    except DatabaseSafetyError:
        pass
    yield

def test_1_uses_fixture(careless_fixture):
    pass

def test_2_must_not_run():
    open(MARKER, "w").write("ran")
"""

UNCAUGHT_IN_TEST = """
from app.core.db_safety import DatabaseSafetyError

def test_1_raises():
    raise DatabaseSafetyError("simulated uncaught violation")

def test_2_must_not_run():
    open(MARKER, "w").write("ran")
"""

NO_VIOLATION = """
def test_1_fine():
    pass

def test_2_runs():
    open(MARKER, "w").write("ran")
"""


def _run_with_suite_conftest(tmp_path: Path, body: str) -> tuple[subprocess.CompletedProcess[str], Path]:
    marker = tmp_path / "second_test_ran"
    test_file = tmp_path / "test_tripwire_probe.py"
    test_file.write_text(f"MARKER = {str(marker)!r}\n" + textwrap.dedent(body), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "tests.conftest", "-p", "no:cacheprovider", "-q",
         "--rootdir", str(tmp_path), str(test_file)],
        cwd=BACKEND_DIR, env=_subprocess_env(), capture_output=True, text=True, timeout=120,
    )
    return result, marker


@pytest.mark.parametrize("body", [SWALLOW_IN_TEST, SWALLOW_IN_FIXTURE, UNCAUGHT_IN_TEST],
                         ids=["swallowed-in-test", "swallowed-in-fixture", "uncaught"])
def test_safety_violation_aborts_the_whole_session(tmp_path, body):
    result, marker = _run_with_suite_conftest(tmp_path, body)
    output = result.stdout + result.stderr
    assert result.returncode == 4, output
    assert "Database safety violation recorded" in output and "simulated" in output
    assert not marker.exists(), "a later test ran after a safety violation"


def test_session_without_violation_runs_normally(tmp_path):
    result, marker = _run_with_suite_conftest(tmp_path, NO_VIOLATION)
    assert result.returncode == 0, result.stdout + result.stderr
    assert marker.exists()
