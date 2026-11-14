# Architecture

A modular monolith: one FastAPI service, one PostgreSQL database, one React single-page app.

```
frontend (React SPA; nginx in Docker) ──/api──▶ backend (FastAPI) ──▶ PostgreSQL
                                                     │
                                                     └─▶ collectors ──▶ Vinnova API · BSP WordPress API · company websites
                                                          (SafeHttpClient: allowlist, SSRF checks, size and time limits)
```

## Backend (`backend/app`)

| Package | Responsibility |
|---|---|
| `core/` | Env-based settings, JSON logging with secret redaction, single clock (`REFERENCE_DATE`) |
| `db/` | Declarative base with naming conventions; engine and sessions (UTC) |
| `models/` | ORM entities, kept separate from API schemas |
| `schemas/` | Pydantic request/response models and validation |
| `security/` | `url_guard` (SSRF-safe HTTP), `auth` (PBKDF2, signed tokens, principals), `deps` (admin token, rate limits) |
| `services/collectors/` | Source registry, collector framework, Vinnova / BSP / evidence-verifier adapters, idempotent store |
| `services/intelligence/` | Taxonomy, concept extraction, profile model, enrichment, editing workflow, geography, search, views (graph, compare, focus, funding, brief), PDF |
| `services/matching/` | Opportunity tagging, opportunity matching, technology relevance, complementarity |
| `services/recommendations/` | Candidate generation, ranking, recompute pipeline (`Workspace`) |
| `services/llm/` | Optional provider adapter with grounding check |
| `api/routes/` | `auth`, `companies` (company-scoped endpoints), `core` (opportunities, sources, collectors, evidence, search, members, demo, health) |
| `seed/` | Evidence-backed company JSON, source snapshots, seeding and demo reset |

## Data model

`sources` → `source_health`, `collection_runs`, `evidence` → `opportunities` (→ `opportunity_technologies`).
`companies` → `company_claims` (typed `source_stated` / `inferred` / `user_provided`, with status and evidence), `company_priorities`, `profile_revisions`, `company_accounts`, `search_history`.
Materialised intelligence: `company_technologies`, `collaboration_recommendations`, `recommendations` (stable `fingerprint`, user `status`) → `saved_recommendations`.

Key constraints: unique `(source_id, external_id)` on opportunities (no duplicates on re-collection); unique `(url, excerpt_hash)` on evidence; check constraint that source-stated claims cite evidence; an ORM `before_flush` guard making source-stated claim content immutable; cascades from companies to company-owned rows. Migrations: `0001_initial_schema`, `0002_regional_intelligence_company_accounts`.

## Recompute pipeline

Runs after collection, profile edits, reviews and priority changes (`services/recommendations/pipeline.py`):

1. **Prepare** — ensure priorities; run rule-based enrichment for every company first (no order-dependent results).
2. **Workspace** — build each company's *private* profile (its own edits) and *public* profile (source facts + inferences only); score every opportunity once per profile.
3. **Per company** — technology relevance, complementarity against other companies' public profiles, recommendation candidates, ranking, persistence. Saved/dismissed status survives recompute via stable fingerprints.

On startup with an existing database, the app applies registry changes, adds newly shipped evidence-backed claims (additively), backfills derived fields after migrations, and recomputes.

## Frontend (`frontend/src`)

`app/` (router, workspace gate, session) · `components/ui` (primitives) · `components/shared` (badges, evidence panel, criteria breakdown) · `components/charts` (technology radar, regional map) · `components/layout` (app shell) · `features/` (opportunity drawer, priority editor) · `pages/` · `services/queries.ts` (TanStack Query hooks) · `lib/` (API client, session store, utils) · `types/api.ts`.

Routes: `/` landing · `/login` · `/app/:companyId/{focus, overview, company, opportunities, technologies, collaboration, recommendations, compare, brief, search, members, sources, settings}`. `WorkspaceGate` ensures the session belongs to the company in the URL.

## Decisions

- **Deterministic first** — every number comes from documented rules; the LLM is optional and cannot change rankings.
- **Concepts, not tokens** — matching uses typed concepts with specificity; generic words are not concepts.
- **Snapshots through the same parser** — offline data is raw API payload replayed through the live code path.
- **Private vs public profiles** give company-level isolation without multi-tenant complexity.
- **Hand-written Tailwind primitives** in the shadcn style instead of the CLI, to keep dependencies small.
