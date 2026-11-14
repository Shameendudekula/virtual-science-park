# Virtual Science Park

**Discover. Connect. Innovate.** An evidence-backed innovation-intelligence prototype for member companies of Blue Science Park (Karlskrona, Blekinge). Built by a solo student developer from Blekinge Institute of Technology for BUILD Hackathon 2026.

> **Status: hackathon prototype.** The application runs end to end: profiles, opportunities, technologies, partners and recommendations. Some requirements of the brief are not yet implemented (see [Current limitations](#current-limitations)). Bundled data is a dated snapshot, not live, unless you run a live collection.

## The challenge

> "How can AI agents help companies discover relevant knowledge, connections and opportunities based on an understanding of their business?" (Blue Science Park challenge brief, p.1)

Blue Science Park wants a Virtual Science Park: a service that understands its 40+ member companies and finds relevant knowledge, events, testing environments, funding and partners for them. The brief's requirements are summarised in [docs/research/challenge-analysis.md](docs/research/challenge-analysis.md) and tracked in [docs/requirements.md](docs/requirements.md).

| | |
|---|---|
| Event | Hackathon 2026 (campor × BUILD) |
| Dates | 13–15 November 2026 |
| Venue | Black Box, Ericsson, Karlskrona, Sweden |
| Challenge | Virtual Science Park (by Blue Science Park) |

## What the application does

- **Company profiles with evidence.** Each source-stated claim quotes the official web page it comes from, with a link and retrieval date. Rule-based inferences and company-provided information are labelled separately. Companies can confirm, reject, correct or add claims.
- **Opportunity radar.** Vinnova funding calls and Blue Science Park news and event metadata, ranked per company with visible scoring criteria. VSP never decides eligibility: when the source contains eligibility text, it is quoted.
- **Technology radar.** Technologies linked to a company's documented capabilities, each with the rule behind its ring.
- **Potential partners.** Suggestions are based on complementary capabilities (a documented need on one side meeting a documented capability on the other), never on shared keywords alone. They are always labelled as potential, never as existing partnerships.
- **Regional relevance.** Karlskrona, Blekinge, Sweden, Europe, International and Online scopes, each with a stated or inferred basis. Online events and national or European funding are not penalised for location.
- **Recommendations.** Prioritised next steps with criteria, evidence and uncertainty, plus a "Your Innovation Opportunities" page for small teams.
- **Company workspaces.** One login per company. A company's private edits and priorities never affect another company's results.

The matching engine is deterministic and needs no AI key. An optional LLM can only reword summaries, and its output is checked against the facts.

## Quick start (local development)

**Prerequisites:** Python 3.12, Node 20+, PostgreSQL 14+.

```bash
# 1. Databases: role "vsp", application database vsp_park, test database vsp_park_test
psql -d postgres -c "CREATE ROLE vsp LOGIN PASSWORD 'vsp' CREATEDB;"   # skip if the role exists
createdb -O vsp vsp_park
createdb -O vsp vsp_park_test

# 2. Configuration
cp .env.example .env              # DATABASE_URL defaults to localhost:5432/vsp_park
                                  # replace every change-me value before sharing the app

# 3. Backend
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --port 8000  # seeds the database on first start

# 4. Frontend (new terminal)
cd frontend
npm ci
npm run dev
```

| What | URL |
|---|---|
| Application | http://localhost:5173 |
| API | http://localhost:8000/api |
| API documentation | http://localhost:8000/api/docs |

**Sign in:** each company has one workspace login (username = company slug, e.g. `ocean-harvesting`; password = `DEMO_COMPANY_PASSWORD` from `.env`). A password sign-in can edit its own company's profile, priorities and saved items. With `DEMO_MODE=true` the login page also offers password-free demo workspaces; these are **read-only** (every page can be explored, nothing can be changed). Resetting the demo and running collectors need the admin token (`ADMIN_TOKEN`).

**Docker (written, not yet executed):** `cp .env.example .env && docker compose up --build`, then open http://localhost:8080.

## Tests and build

**No-database tests** (no PostgreSQL needed): database fixtures are skipped and the test URL points at a closed local port, so no connection is made.

```bash
cd backend && VSP_TEST_NO_DB=1 pytest
cd frontend && npm test && npm run build
```

**Full database-backed tests** drop and recreate the `public` schema of the target database (then apply the Alembic migrations and seed it). Run them only against a dedicated, isolated test database, never against `vsp`, `vsp_test`, `vsp_park` or `vsp_park_test`. `vsp_park_test` is the suite's built-in default when `TEST_DATABASE_URL` is unset, so always set it explicitly. `backend/tests/conftest.py` checks these before anything connects and aborts with exit code 4 if one fails:

| Variable | Requirement |
|---|---|
| `TEST_DATABASE_URL` | Names the isolated test database and states its port explicitly |
| `VSP_ALLOW_TEST_DATABASE` | The name of that database; must end with `_test` and can never be a protected database |
| `VSP_TEST_EXPECTED_PORT` | Must equal the port in `TEST_DATABASE_URL` |
| `VSP_TEST_EXPECTED_SYSTEM_ID` | Optional: the server's system identifier; any connection to a different server is refused |

With those set, run `cd backend && pytest`. Every connection, and the schema reset itself, re-checks the database name, port and (if given) system identifier; see [docs/vsp/security.md](docs/vsp/security.md#database-and-configuration-safety).

## Configuration

All settings are in [.env.example](.env.example). The ones you are most likely to change:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection (Docker Compose sets its own). Must name `vsp_park` or `vsp_park_test`; `vsp`, `vsp_test` and system databases are always refused |
| `VSP_ALLOW_DATABASE` | Deliberate opt-in for one other database name (never a protected one) |
| `ENVIRONMENT` | `development`, `test` or `production`. Production refuses demo mode, weak or placeholder secrets and the `vsp:vsp` database credentials |
| `SECRET_KEY` | Signs workspace sessions. If empty, a random key is generated at each start. |
| `ADMIN_TOKEN` | Required to run collectors and to reset the demo (`X-Admin-Token` header), also in demo mode |
| `DEMO_COMPANY_PASSWORD` | Password for the seeded company accounts |
| `DEMO_MODE` | Password-free, read-only demo login. Off by default; `.env.example` turns it on for the local demo. Refused in production |
| `REFERENCE_DATE` | Pins "today" for a reproducible demo |
| `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY` | Optional summary rewording (`anthropic`; needs `pip install ".[llm]"`) |

## Current limitations

**Ask VSP boundaries (implemented with deterministic rules, no LLM):** every question is classified before any search runs. Relevant questions get ranked records; unrelated requests get the service's remit and suggested questions; override and prompt-injection attempts and requests for private company data are declined; eligibility questions get potential matches with a notice that VSP does not assess eligibility or guarantee funding; questions that need a person are referred to Blue Science Park staff via its official website. Each message is checked on its own, so follow-ups get the same rules. Limits: keyword rules can miss unusual wording; vague requests are declined rather than answered with a clarifying question; it is structured search, not a conversational assistant.

**Demo access and privacy:**
- Demo sessions are read-only, enforced by the API (`403` on every change); a password session can change only its own company's data; demo reset and collectors require the admin token.
- Searches made in a demo session are not stored, and demo sessions cannot read question history. Question history recorded before this change (including searches by earlier demo visitors) may still be stored and visible to the company account owner; the demo reset does not clear it.

**Not yet implemented (brief requirements):**
- **Runtime profiling agent (FR-P01–P03, FR-P13).** Company profiles are curated seed files whose quotes were verified verbatim against the official pages; a collector re-checks them. No agent fetches and extracts profiles at runtime.
- **Brief-format details.** The brief's six claim categories and per-claim priority flag, event audience and dates, "what changed" summaries for updates, the exact "Potential match — eligibility not assessed" label, a banned-phrase check and a persistent prototype banner are missing or only partly implemented.

**Database and configuration safety** (see [docs/vsp/security.md](docs/vsp/security.md#database-and-configuration-safety)):
- The app, Alembic, the Docker entrypoint and the tests refuse the earlier prototype's `vsp` and `vsp_test` databases and the system databases, refuse URLs without a database name, and check the actual connected database name on every new connection.
- The test suite runs only against `vsp_park_test` (or an explicit `VSP_ALLOW_TEST_DATABASE` ending in `_test`) and re-checks the connected database immediately before it drops the schema.
- `.env` is read only from this repository. Demo mode is off unless `.env` turns it on. Docker Compose publishes its ports on 127.0.0.1 only.

**Known risks, not yet fixed:**
- **Migration IDs.** The migrations use the revision IDs `0001` and `0002`, the same IDs an earlier prototype used for a different schema. The guards above stop them reaching `vsp`/`vsp_test`, but a copy of that schema under another name would still be mis-detected.
- **Database-backed tests need an isolated server.** The full suite has been run against an isolated test database (`TEST_DATABASE_URL` plus `VSP_TEST_EXPECTED_PORT`); this says nothing about any deployed environment, which has not been verified.

**Other:**
- Bundled data was collected on 13 November 2026. Run *Collect live* on the Data Sources page (admin token required) to refresh it.
- Blue Science Park content is used as metadata only (title, date, link). Event dates and venues are not available.
- Ymner is linked, not integrated: its API requires authentication and no reuse terms were found.
- Scores are explainable heuristics, not probabilities.
- No Python dependency lock file yet. Docker Compose has not been run.

## Documentation

**The running application** (`docs/vsp/`):

| Document | Contents |
|---|---|
| [architecture.md](docs/vsp/architecture.md) | Modules, data model, recompute pipeline |
| [data-sources.md](docs/vsp/data-sources.md) | Sources, provenance, validation rules, Ymner findings |
| [matching-methodology.md](docs/vsp/matching-methodology.md) | Scoring criteria, regional relevance, recommendation tiers |
| [security.md](docs/vsp/security.md) | Authentication, isolation, outbound-request protection, data quality |
| [testing.md](docs/vsp/testing.md) | Test suites and what they cover |
| [demo-guide.md](docs/vsp/demo-guide.md) | Five-minute demo script |

**Project planning and requirements** (`docs/`): these were written before implementation. Some describe an earlier, unimplemented design and have not been updated. In particular, [architecture.md](docs/architecture.md), [api-contract.md](docs/api-contract.md), [testing.md](docs/testing.md), [handover.md](docs/handover.md) and [solution-overview.md](docs/solution-overview.md) do not describe the running application.

| Document | Purpose |
|---|---|
| [requirements.md](docs/requirements.md) | Official and team requirements, priorities, open questions |
| [research/challenge-analysis.md](docs/research/challenge-analysis.md) | The official brief with page references |
| [research/use-cases.md](docs/research/use-cases.md) | Actors, journey, use cases |
| [decisions.md](docs/decisions.md) | Decision log (some decisions differ from the implementation, e.g. D-007 SQLite and D-012 simulated sign-in) |
| [security-privacy.md](docs/security-privacy.md) | Planned security, privacy and interaction boundaries |
| [sources.md](docs/sources.md) | Source register |
| [design/](docs/design/) | Product vision, information architecture, screens, design system |
| [quality-boundary-check.md](docs/quality-boundary-check.md), [pitch-outline.md](docs/pitch-outline.md), [team-roles.md](docs/team-roles.md) | Deliverable drafts and roles |

## Data and licensing

Vinnova data comes from its public open-data API, with attribution and links; contact persons are not collected. Blue Science Park content is used as metadata only, because reuse rights were not confirmed. Company facts are short, attributed excerpts that support specific claims. This is a hackathon prototype, not affiliated with or endorsed by the organisations whose public data it displays.
