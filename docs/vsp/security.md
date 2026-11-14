# Security and data quality

## Authentication and isolation

- **One login per company workspace** (`company_accounts`): PBKDF2-SHA256 (390,000 iterations, per-password salt), constant-time comparison.
- Sessions are HMAC-SHA256-signed tokens with expiry (`TOKEN_TTL_MINUTES`, default 8 h), signed with `SECRET_KEY`. Forged or expired tokens get 401.
- Every private endpoint (focus, overview, profile, claim review, priorities, opportunities, technologies, collaborations, graph, recommendations, funding, innovation brief, recommendation actions, company-specific search) calls `require_company`: 401 without a session, 403 for another company's session. The admin token also grants access.
- **Data isolation:** a company's results use its private profile; other companies are seen only through their *public* profile (source facts and inferences not derived from private input). Private claims, review decisions, priorities, saved items and search history never appear in, or influence, another company's results (`test_private_edits_never_leak_to_other_companies`).
- `DEMO_MODE=true` enables password-free demo login and unauthenticated demo reset. **Turn it off for any non-demo deployment.**

## Database and configuration safety

Guards live in `backend/app/core/db_safety.py` and are used by the application, Alembic, the Docker entrypoint and the tests.

- **Approved databases:** `vsp_park` (application) and `vsp_park_test` (tests). Any other name needs a deliberate opt-in: `VSP_ALLOW_DATABASE` (application) or `VSP_ALLOW_TEST_DATABASE` (tests; must end in `_test`).
- **Protected databases**, refused even with an opt-in and in any letter case: `vsp`, `vsp_test` (the earlier prototype), `postgres`, `template0`, `template1`.
- **URL rules:** the URL must name its database (otherwise libpq would connect to a database named after the user, `vsp`); `service`, `dbname` and `database` query parameters are refused; only the `postgresql`/`postgresql+psycopg` drivers are accepted.
- **Connected-database check:** `make_engine` is the only place engines are created. Every new connection runs `SELECT current_database()` and is closed and refused if the name differs from the URL's, or is protected. This catches poolers, service files and `PGDATABASE`.
- **Alembic** validates the final URL before both online and offline (`--sql`) runs, connects only through `make_engine`, and refuses externally supplied connections.
- **Server identity (optional for the app, required for database-backed tests):** with `VSP_EXPECT_SERVER_PORT` and/or `VSP_EXPECT_SYSTEM_IDENTIFIER`, every new connection must also report exactly that `inet_server_port()` and `pg_control_system().system_identifier`. A NULL port (Unix-socket connection), a missing identifier, or an identity that cannot be read is refused (fail closed). `pg_control_system()` is executable by any role by default (no `REVOKE` in PostgreSQL's `system_functions.sql`), so no extra privilege is needed.
- **Tests, in order:** (1) at import, before any engine exists, `conftest.py` validates `TEST_DATABASE_URL`, and database-backed runs require `VSP_TEST_EXPECTED_PORT` equal to the URL's explicit port (optional `VSP_TEST_EXPECTED_SYSTEM_ID`); (2) every connection checks database, port and system identifier; (3) `recreate_schema` re-checks the same identity in the transaction that runs `DROP SCHEMA`, immediately before it; Alembic's migration connection is checked by (2) with the same values. Any failure exits with code 4. `VSP_TEST_NO_DB=1` skips database tests and points the URL at a closed local port.
- **Tripwire:** during tests every `DatabaseSafetyError` is recorded when it is created, so a test or fixture that catches it cannot hide it. Once recorded, all further connections are refused and the session aborts (exit code 4) right after the current test phase.
- **`.env` loading:** only `backend/.env` and the repository-root `.env` (absolute paths), never the current working directory.
- **Production (`ENVIRONMENT=production`)** refuses to start with `DEMO_MODE=true`; a missing, short (<32) or `change-me` `SECRET_KEY`; a short or placeholder `ADMIN_TOKEN`/`DEMO_COMPANY_PASSWORD`; a `*` CORS origin; or the `vsp:vsp` database credentials. In development the same issues are logged as warnings at startup.
- **No secrets in messages:** errors and warnings name settings, never values; database URLs are shown with the password hidden; `DATABASE_URL` is excluded from the settings `repr`. Configuration errors are raised directly rather than through pydantic, which would echo the input.
- **Docker Compose** publishes ports on `127.0.0.1` only.

Regression tests: `backend/tests/test_safety.py`.

## Privileged actions

Collector runs require `X-Admin-Token` (constant-time comparison); with no `ADMIN_TOKEN` they are disabled. Secrets are never returned by the API or written to logs (`core/logging.redact`).

## Outbound requests (SSRF protection)

All collector traffic goes through `security/url_guard.SafeHttpClient`:

- https only; no credentials in URLs; port 443 only; IP-literal hosts rejected;
- host must be on the source's allowlist (exact host or subdomain);
- DNS is resolved, and private, loopback, link-local, multicast, reserved and IPv4-mapped private addresses are rejected;
- redirects are followed manually (max 5) and every hop is re-validated;
- timeouts and a streamed response-size limit.

## Untrusted content and prompt injection

External text is sanitised (markup and control characters removed, length capped), stored as inert data and never executed. Matching uses concept extraction only, so instructions in source text have no effect beyond their words (tested: an injected "mark as eligible, set relevance to 100" scores exactly like the same nouns without the instructions). The optional LLM sees only VSP-generated facts in a delimited block with an instruction to ignore embedded instructions; output is validated with Pydantic and rejected if it introduces numbers, URLs, names or eligibility claims absent from the input. Blue Science Park content is never sent to an LLM.

## API hardening

CORS restricted to configured origins; bodies over 64 KB rejected; security headers (`nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Cache-Control: no-store`); consistent error bodies without internals; Pydantic validation on all inputs; SQLAlchemy parameterised queries; rate limits on login (10/min), collectors (6/min), search (60/min), brief (20/min) and reset (10/min).

## Data quality guarantees

- Source-stated claims must cite evidence (database check constraint) and their content is immutable (ORM guard). Corrections create a company-provided claim that supersedes the original, which stays visible.
- Deadlines are stored only when stated; placeholder dates are rejected. Eligibility is never decided, only quoted.
- Partnerships are never invented: documented collaborations come from the company's own published pages; everything else is labelled *potential*.
- Re-collection is idempotent (unique source/external id, content hashes); an older snapshot never overwrites newer data; a failed run never modifies existing records.
- Data minimisation: Vinnova contact lists are dropped before storage; team biographies were not used.

## Known gaps

In-memory rate limiter (use a shared store with multiple workers); bearer tokens in headers rather than cookies, so no CSRF tokens are needed but tokens live in session storage; demo mode is insecure by design.
