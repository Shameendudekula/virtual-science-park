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
- **Ask VSP.** A question box for supported discovery tasks. Every question is first checked by deterministic boundary rules:
  - Supported questions (funding, testing, technology, partners, events, business development) are answered with the existing structured search: ranked database records with their reasons, not generated text.
  - Eligibility questions can return potential matches, with a notice that VSP does not determine formal eligibility or guarantee funding.
  - Requests that need a person (decisions, commitments, professional advice) are referred to Blue Science Park staff through its official website.
  - Unrelated requests, attempts to override the service's rules and requests for private company data are declined with a fixed explanation.

  Ask VSP is not a generative AI chatbot.

Generative LLM functionality is disabled in the demo configuration. The current recommendation and matching workflows use deterministic logic and need no AI key. The code contains an optional integration that can only reword the executive summary, and its output is checked against the facts; it is not enabled in the demo configuration.

## Data sources

All bundled data was collected on **13 November 2026** and is loaded as a dated snapshot when the database is first seeded. Nothing is queried continuously: an administrator can start a new collection from the Data Sources page (admin token required). Every record keeps its source link, retrieval date and provenance label (*Collected snapshot* or *Live data*).

| Source | What it contributes | In the bundled snapshot |
|---|---|---|
| [Vinnova open-data API](https://data.vinnova.se/api/) | Funding opportunities: application rounds with titles, deadlines and call text where stated. Contact persons are not collected. | 56 application rounds (and 44 calls, used for programme names) |
| [Blue Science Park website](https://www.bluesciencepark.se/) (public WordPress API) | The member directory (used to verify membership), plus news and event listings. Used as **metadata only** (title, publication date, link), because reuse rights were not confirmed. Event dates, venues, organisers and sponsors are not in the collected data. | 56 member listings, 100 news posts, 50 event listings |
| Official company websites | Short quoted excerpts that support each source-stated claim in the 7 detailed company profiles. An admin-only check can re-fetch the pages to confirm each excerpt is still there. | Evidence for 7 profiled companies |

Ymner is shown as an external link only (its API requires authentication), and the EU Funding & Tenders Portal is a disabled placeholder. Neither contributes data. Details: [docs/vsp/data-sources.md](docs/vsp/data-sources.md).

## Architecture

```text
Public sources:
Vinnova API  |  Blue Science Park website  |  Official company websites
                             |
            Collectors (bundled snapshot at first start;
              live run only on an admin request)
                             |
          Stored records with source link, retrieval
              date and provenance (snapshot / live)
                             |
React + TypeScript (Vite)  <-- HTTP API -->  FastAPI
                             |
    Profiles and evidence · opportunity matching · technology radar ·
    partner complementarity · recommendations · Ask VSP boundary rules
                             |
                         PostgreSQL

Optional LLM wording of the executive summary (not enabled in the demo configuration).
```

Code: `backend/app/services/collectors` (data collection), `intelligence` (profiles, search, Ask VSP boundaries), `matching` and `recommendations` (deterministic scoring and ranking), `llm` (the optional wording step). More detail: [docs/vsp/architecture.md](docs/vsp/architecture.md).

## Security and demo access

Permissions are enforced by the backend on every request. Disabled buttons in the interface are only a convenience; they are not the security boundary.

- **Public demo sessions are read-only.** With demo mode on, anyone can open a demonstration company workspace without a password and explore every page, but every change is refused by the API (HTTP 403).
- **Company sessions can change only their own company.** Signing in with the company's username and password allows editing that company's profile, priorities and saved items. Another company's data is refused (403).
- **Admin-only operations.** Running data collectors and resetting the demo require the admin token, also in demo mode. A company session never grants admin rights.
- **Sessions** are signed tokens that expire; forged, modified or malformed tokens are refused (401).
- **Search privacy.** Questions asked in a demo session are not stored, and demo sessions cannot read question history. History recorded before this rule existed (which may include earlier demo visitors' questions) has not been deleted and may be visible to the company account owner; the demo reset does not clear it.
- **Rate limits** on sign-in, demo sign-in, changes, search, the innovation brief, collectors and reset.

Details: [docs/vsp/security.md](docs/vsp/security.md).

## Quick start (local development)

**Prerequisites:** Python 3.12, Node 20+, PostgreSQL 14+, and a **dedicated PostgreSQL database for this app that you create and own**. It must not be one of the protected databases: `vsp`, `vsp_test`, `vsp_park` or `vsp_park_test`.

> **Database-safety refactor pending.** Project policy treats `vsp`, `vsp_test`, `vsp_park` and `vsp_park_test` as protected: never use them for development, tests or schema changes. The code does not fully enforce this policy yet. It always refuses `vsp` and `vsp_test`, but still accepts `vsp_park` (application) and `vsp_park_test` (tests) as built-in names, and `.env.example` and Docker Compose still default to `vsp_park`. Until the refactor is done, do not rely on any default: configure your dedicated database explicitly as shown below.

```bash
# 1. Configuration
cp .env.example .env
# Edit .env before starting anything:
#   DATABASE_URL        -> your dedicated database (the example value points at vsp_park: change it)
#   VSP_ALLOW_DATABASE  -> the name of that database (any other name is refused without this opt-in)
#   replace every change-me value before sharing the app

# 2. Backend
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head              # creates the tables in the database named in DATABASE_URL
uvicorn app.main:app --port 8000  # seeds that database on first start

# 3. Frontend (new terminal)
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

**Docker (written, not yet executed):** Docker Compose currently creates and uses a database named `vsp_park` unless `.env` sets `POSTGRES_DB` (and a matching `VSP_ALLOW_DATABASE`) to a dedicated name. Under the project policy that default is protected, so do not run it unchanged; the Compose setup is part of the pending database-safety refactor.

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

## Verification

**Latest local verification (no database used):**

| Check | Result |
|---|---|
| Backend tests, no-database mode (`VSP_TEST_NO_DB=1`) | 237 passed, 78 skipped (the skipped tests need a database) |
| Frontend tests (Vitest) | 49 passed |
| TypeScript typecheck | Passed |
| Frontend production build | Passed |

**Previous database-backed run:** before the final frontend and documentation changes, the full backend suite passed **314 tests, with 1 skipped**, against a separate, isolated test database. That was an earlier run, not part of the latest verification above.

These are local results. The deployed application has not been verified by these checks.

## Configuration

All settings are in [.env.example](.env.example). The ones you are most likely to change:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection to your dedicated database (Docker Compose sets its own). `vsp`, `vsp_test` and system databases are always refused. The code still accepts `vsp_park` and `vsp_park_test` without an opt-in, but project policy treats them as protected (refactor pending), so never point it at them |
| `VSP_ALLOW_DATABASE` | Explicit opt-in naming your dedicated database (required for any name other than the built-in ones; can never allow `vsp` or `vsp_test`) |
| `ENVIRONMENT` | `development`, `test` or `production`. Production refuses demo mode, weak or placeholder secrets and the `vsp:vsp` database credentials |
| `SECRET_KEY` | Signs workspace sessions. If empty, a random key is generated at each start. |
| `ADMIN_TOKEN` | Required to run collectors and to reset the demo (`X-Admin-Token` header), also in demo mode |
| `DEMO_COMPANY_PASSWORD` | Password for the seeded company accounts |
| `DEMO_MODE` | Password-free, read-only demo login. Off by default; `.env.example` turns it on for the local demo. Refused in production |
| `REFERENCE_DATE` | Pins "today" for a reproducible demo |
| `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY` | Optional summary rewording (`anthropic`; needs `pip install ".[llm]"`) |

## Current limitations

**Ask VSP limits:** the boundary rules are keyword-based and can miss unusual wording; vague requests are declined rather than answered with a clarifying question; each message is checked on its own (there is no conversation memory); it is structured search, not a conversational assistant.

**Not yet implemented (brief requirements):**
- **Runtime profiling agent (FR-P01–P03, FR-P13).** Company profiles are curated seed files whose quotes were verified verbatim against the official pages; a collector re-checks them. No agent fetches and extracts profiles at runtime.
- **Brief-format details.** The brief's six claim categories and per-claim priority flag, event audience and dates, "what changed" summaries for updates, the exact "Potential match — eligibility not assessed" label, a banned-phrase check and a persistent prototype banner are missing or only partly implemented.

**Database and configuration safety** (see [docs/vsp/security.md](docs/vsp/security.md#database-and-configuration-safety)):
- The app, Alembic, the Docker entrypoint and the tests refuse the earlier prototype's `vsp` and `vsp_test` databases and the system databases, refuse URLs without a database name, and check the actual connected database name on every new connection.
- The test suite runs only against `vsp_park_test` (or an explicit `VSP_ALLOW_TEST_DATABASE` ending in `_test`) and re-checks the connected database immediately before it drops the schema.
- `.env` is read only from this repository. Demo mode is off unless `.env` turns it on. Docker Compose publishes its ports on 127.0.0.1 only.

**Known risks, not yet fixed:**
- **Migration IDs.** The migrations use the revision IDs `0001` and `0002`, the same IDs an earlier prototype used for a different schema. The guards above stop them reaching `vsp`/`vsp_test`, but a copy of that schema under another name would still be mis-detected.
- **No deployment verified.** The test results in [Verification](#verification) are local; no deployed environment has been checked by them.

**Other:**
- Bundled data was collected on 13 November 2026. Run *Collect live* on the Data Sources page (admin token required) to refresh it.
- Blue Science Park content is used as metadata only (title, date, link). Event dates and venues are not available.
- Ymner is linked, not integrated: its API requires authentication and no reuse terms were found.
- Scores are explainable heuristics, not probabilities.
- No Python dependency lock file yet. Docker Compose has not been run.

## Project links

- **Repository:** https://github.com/Shameendudekula/virtual-science-park
- **Submitted branch:** [`deploy/render-demo`](https://github.com/Shameendudekula/virtual-science-park/tree/deploy/render-demo)
- **Live demo:** a link will be added here once the latest deployment has been verified.

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
