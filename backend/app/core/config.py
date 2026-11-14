"""Environment-based configuration. No secrets are hard-coded; all come from env / .env.

Safety rules enforced here (see app/core/db_safety.py and docs/vsp/security.md):
* ``.env`` files are read only from inside this repository (``backend/.env`` and the repository-root ``.env``),
  never relative to the current working directory.
* ``DATABASE_URL`` must name an approved database (vsp_park, vsp_park_test or a ``VSP_ALLOW_DATABASE`` opt-in) and
  never a protected one.
* ``ENVIRONMENT=production`` refuses demo mode, missing or placeholder secrets and the development database password.
Validation failures raise ``ConfigurationError`` whose message names settings but never their values.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.db_safety import (
    DatabaseSafetyError,
    parse_and_check,
    parse_expected_port,
    parse_expected_system_identifier,
    validate_database_url,
)

BACKEND_DIR = Path(__file__).resolve().parents[2]
PLACEHOLDER_MARKER = "change-me"
DEV_DB_CREDENTIALS = ("vsp", "vsp")


def env_files(backend_dir: Path = BACKEND_DIR) -> tuple[Path, ...]:
    """Repository-local env files, lowest priority first (pydantic-settings: later files win).

    The repository-root .env is used only when the expected layout exists (``<root>/backend`` is this backend),
    so in a container (backend copied to /app) the filesystem root is never consulted.
    """
    backend_dir = backend_dir.resolve()
    files = [backend_dir / ".env"]
    root = backend_dir.parent
    if (root / "backend").resolve() == backend_dir:
        files.append(root / ".env")
    return tuple(files)


class ConfigurationError(RuntimeError):
    """Invalid configuration. Raised directly (not wrapped by pydantic) so values are never echoed."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=env_files(), env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Virtual Science Park"
    environment: str = Field(default="development", description="development | test | production")
    database_url: str = Field(default="postgresql+psycopg://vsp:vsp@localhost:5432/vsp_park", repr=False)
    # Deliberate opt-in for a database other than vsp_park / vsp_park_test. Never allows a protected database.
    vsp_allow_database: str = ""
    # Optional server identity, checked on every new connection when set (empty = not checked).
    vsp_expect_server_port: str = ""
    vsp_expect_system_identifier: str = ""

    # Comma-separated list of allowed browser origins for CORS.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080"

    # Signs company workspace session tokens. Required (32+ characters) in production.
    secret_key: SecretStr = SecretStr("")
    token_ttl_minutes: int = 480
    # Password given to seeded company accounts (username = company slug). Empty = random (login only via demo mode).
    demo_company_password: SecretStr = SecretStr("")

    # Admin token protects collector runs and (outside demo mode) demo reset. Empty = disabled.
    admin_token: SecretStr = SecretStr("")
    # Off unless explicitly enabled (DEMO_MODE=true in .env for local demos). Refused in production.
    demo_mode: bool = False

    # Seed the database on startup if it is empty.
    auto_seed: bool = True

    # Outbound HTTP for collectors.
    http_timeout_seconds: float = 20.0
    http_max_response_bytes: int = 15 * 1024 * 1024
    http_user_agent: str = "VirtualSciencePark/1.0 (+innovation-intelligence research prototype)"
    collector_min_interval_seconds: int = 30

    # Optional LLM provider. The application never requires it.
    llm_provider: str = "none"  # none | anthropic
    llm_model: str = ""
    llm_api_key: SecretStr = SecretStr("")
    llm_base_url: str = ""
    llm_timeout_seconds: float = 30.0

    # Reference "today" override for reproducible demos/tests (ISO date). Empty = real clock.
    reference_date: str = ""

    log_level: str = "INFO"

    @field_validator("environment")
    @classmethod
    def _env(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in {"development", "test", "production"}:
            raise ValueError("environment must be development, test or production")
        return v

    @model_validator(mode="after")
    def _safety(self) -> Settings:
        try:
            validate_database_url(self.database_url, extra_allowed=[self.vsp_allow_database])
        except DatabaseSafetyError as exc:
            raise ConfigurationError(f"DATABASE_URL rejected: {exc}") from None
        try:
            parse_expected_port(self.vsp_expect_server_port, name="VSP_EXPECT_SERVER_PORT")
            parse_expected_system_identifier(self.vsp_expect_system_identifier, name="VSP_EXPECT_SYSTEM_IDENTIFIER")
        except DatabaseSafetyError as exc:
            raise ConfigurationError(str(exc)) from None
        if self.environment == "production":
            problems = self.production_problems()
            if problems:
                raise ConfigurationError("Refusing to start in production: " + "; ".join(problems))
        return self

    # ------------------------------------------------------------------------------------------- checks
    def _uses_dev_db_password(self) -> bool:
        try:
            url = parse_and_check(self.database_url)
        except DatabaseSafetyError:
            return False
        return (url.username, url.password) == DEV_DB_CREDENTIALS

    def production_problems(self) -> list[str]:
        """Reasons the configuration is unsafe for production. Names settings, never values."""
        problems: list[str] = []
        secret = self.secret_key.get_secret_value()
        admin = self.admin_token.get_secret_value()
        demo_pw = self.demo_company_password.get_secret_value()
        if self.demo_mode:
            problems.append("DEMO_MODE must be false")
        if not secret:
            problems.append("SECRET_KEY must be set")
        elif len(secret) < 32 or PLACEHOLDER_MARKER in secret.lower():
            problems.append("SECRET_KEY must be at least 32 characters and not a placeholder")
        if admin and (len(admin) < 24 or PLACEHOLDER_MARKER in admin.lower()):
            problems.append("ADMIN_TOKEN must be at least 24 characters and not a placeholder (or empty to disable)")
        if demo_pw and (len(demo_pw) < 12 or PLACEHOLDER_MARKER in demo_pw.lower()):
            problems.append("DEMO_COMPANY_PASSWORD must be at least 12 characters and not a placeholder (or empty)")
        if "*" in self.cors_origins:
            problems.append("CORS_ORIGINS must not contain a wildcard")
        if self._uses_dev_db_password():
            problems.append("DATABASE_URL must not use the development credentials")
        return problems

    def security_warnings(self) -> list[str]:
        """Non-fatal warnings for development and test. Names settings, never values."""
        warnings: list[str] = []
        if self.demo_mode:
            warnings.append(
                "DEMO_MODE is on: password-free demo login and demo reset are enabled. Never expose this server."
            )
        if not self.secret_key.get_secret_value():
            warnings.append(
                "SECRET_KEY is not set: an ephemeral key is used and sessions end when the server restarts."
            )
        for name, value in (("SECRET_KEY", self.secret_key), ("ADMIN_TOKEN", self.admin_token),
                            ("DEMO_COMPANY_PASSWORD", self.demo_company_password)):
            if PLACEHOLDER_MARKER in value.get_secret_value().lower():
                warnings.append(f"{name} still has a placeholder value; replace it before sharing the server.")
        return warnings

    @property
    def expected_server_port(self) -> int | None:
        return parse_expected_port(self.vsp_expect_server_port, name="VSP_EXPECT_SERVER_PORT")

    @property
    def expected_system_identifier(self) -> str | None:
        return parse_expected_system_identifier(self.vsp_expect_system_identifier, name="VSP_EXPECT_SYSTEM_IDENTIFIER")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def llm_enabled(self) -> bool:
        return self.llm_provider != "none" and bool(self.llm_api_key.get_secret_value())


@lru_cache
def get_settings() -> Settings:
    return Settings()
