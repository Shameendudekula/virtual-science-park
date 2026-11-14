# Decision Log

Record significant project decisions here. Add new entries at the bottom and never edit an accepted decision. If a decision changes, add a new entry that supersedes the old one.

## Template

```markdown
### D-XXX: Title

- **Date:** YYYY-MM-DD
- **Status:** Proposed | Accepted | Superseded by D-YYY
- **Context:** Why a decision is needed.
- **Decision:** What was decided.
- **Consequences:** Trade-offs and follow-up work.
```

## Archived Decisions (previous challenge)

D-001 to D-003 belonged to the team's earlier preparation for the Ericsson "Data Storage Optimization" challenge. Their full text is preserved in commit `4ff4384` on the `archive/ericsson-preparation` branch. They do not apply to this project. Numbering continues from D-004 so that IDs stay unique across the history.

| ID | Title | Status |
|---|---|---|
| D-001 | Select the Ericsson Data Storage Optimization challenge | Superseded by D-004 |
| D-002 | Working product name "SmartArchive AI" | Withdrawn (superseded by D-004) |
| D-003 | Tool is non-destructive (previous challenge) | Withdrawn (superseded by D-004) |

## Decisions

### D-004: Switch to the Blue Science Park "Virtual Science Park" challenge

- **Date:** 2026-11-12
- **Status:** Accepted
- **Context:** The team changed its hackathon challenge.
- **Decision:** All work targets the Blue Science Park — Virtual Science Park challenge. Earlier preparation stays in Git history only.
- **Consequences:** All documentation was rewritten on `feat/blue-science-park`. Official requirements must be checked against the written brief ([Q-01](requirements.md#q-open-questions)).

### D-005: Frontend stack: React, TypeScript, Vite, Tailwind CSS

- **Date:** 2026-11-12
- **Status:** Proposed
- **Context:** A small single-page UI is needed quickly, and the team is familiar with React.
- **Decision:** React + TypeScript built with Vite, styled with Tailwind CSS.
- **Consequences:** Types for API schemas should be generated from, or kept in line with, the backend OpenAPI schema.

### D-006: Backend stack: Python, FastAPI, Pydantic

- **Date:** 2026-11-12
- **Status:** Proposed
- **Context:** Fetching, text processing, LLM calls and schema validation are all well supported in Python.
- **Decision:** FastAPI with Pydantic models as the single definition of request, response and LLM-output schemas.
- **Consequences:** The OpenAPI schema comes for free; LLM structured output can be validated with the same models (FR-S03).

### D-007: SQLite with SQLAlchemy; no Alembic in the MVP

- **Date:** 2026-11-12
- **Status:** Proposed
- **Context:** A single-file database is enough for a three-day demo. Schemas will change often during the hackathon.
- **Decision:** SQLite through SQLAlchemy. The database is rebuilt by the demo build script instead of being migrated. Add Alembic only once data must survive schema changes.
- **Consequences:** No migration overhead. Local data is disposable; the durable inputs are the member list and source configuration in `data/config/` and the dated snapshots in `data/snapshots/`.

### D-008: Provider-independent LLM gateway with structured output

- **Date:** 2026-11-12
- **Status:** Proposed
- **Context:** The provider is not chosen, and external processing may be restricted ([Q-05](requirements.md#q-open-questions)).
- **Decision:** All LLM calls go through one internal interface that takes a Pydantic output model and returns validated objects. The provider, model and key come from configuration. Responses are cached by input hash.
- **Consequences:** Provider choice stays open (pending decision below). A local or mock provider enables offline tests and demos.

### D-009: Modular monolith with in-process background jobs

- **Date:** 2026-11-12
- **Status:** Proposed (job-execution part superseded by D-017)
- **Context:** Three developers, three days.
- **Decision:** One backend process. Jobs run as FastAPI background tasks and are tracked in the `research_jobs` table. No queue, broker or microservices.
- **Consequences:** Jobs are lost if the process restarts, which is acceptable for the demo. A queue is an extension point.

### D-010: "Verified" is decided by code-level quote validation

- **Date:** 2026-11-12
- **Status:** Superseded by D-016
- **Context:** The brief requires distinguishing verified facts from AI-inferred interests (BR-05). An LLM's own claim that something is verified is not trustworthy.
- **Decision:** A claim is `verified` only if its quote is found, after normalisation, in the stored text of the cited page (FR-P06). Otherwise it is `inferred`.
- **Consequences:** Paraphrased or translated facts become `inferred` even if correct. The company can confirm them in review.

### D-011: Deterministic matching; LLM used only for explanations

- **Date:** 2026-11-12
- **Status:** Proposed
- **Context:** Rankings must be reproducible and visibly different between companies (BR-13), and explanations must cite real claims (BR-09).
- **Decision:** The score combines topic-tag overlap and keyword similarity (e.g. TF-IDF), computed in code. The LLM writes explanations from the cited claims only, with a template fallback.
- **Consequences:** Rankings are testable (FR-M05). Semantic recall is weaker than with embeddings, which are an extension point.

### D-012: Simulated per-company access tokens in the demo

- **Date:** 2026-11-12
- **Status:** Proposed
- **Context:** BR-10 requires preventing access to other companies' non-public information. Real authentication is out of scope for three days.
- **Decision:** Each demo company has a seeded token. Company-scoped endpoints enforce it. The UI labels the login as simulated.
- **Consequences:** Shows the access-control logic but not production identity. To be confirmed with organisers ([Q-07](requirements.md#q-open-questions)).

### D-013: Testing tools: pytest (backend), Vitest + React Testing Library (frontend)

- **Date:** 2026-11-12
- **Status:** Proposed
- **Context:** Security and boundary tests are P0. The frontend needs light component tests for labels and badges.
- **Decision:** Use pytest with FastAPI's test client for the backend. Use Vitest with React Testing Library for the frontend. Use axe-core for basic automated accessibility checks (added 2026-11-12 for FR-U08).
- **Consequences:** CI is optional; tests must at least run locally before merging.

### D-014: Monitoring areas: funding, events, and knowledge/trend updates

- **Date:** 2026-11-12
- **Status:** Accepted
- **Context:** The brief asks teams to "choose one or two [monitoring areas] and demonstrate them convincingly" (p.1 Scope).
- **Decision:** Build funding opportunities (brief area 4) plus events and knowledge/trend updates (brief areas 2 and 1). Events and updates are planned to come from the same source (S3 in [sources.md](sources.md)).
- **Consequences:** This covers three of the brief's areas, one more than the suggested "one or two" (raised as [Q-13](requirements.md#q-open-questions)). **Cut rule:** if events and funding are not working end to end by the end of day 2, knowledge/trend updates (FR-O07, BR-26) move to P1, leaving two areas.

### D-015: Assistant interface: simple ask-box with a response panel

- **Date:** 2026-11-12
- **Status:** Accepted
- **Context:** The brief requires appropriate responses to relevant, unrelated and boundary-override requests (p.1 Scope) and applies boundaries to follow-ups (p.3).
- **Decision:** One ask-box with a response panel, in the context of the selected company. The last 3 exchanges are kept for follow-ups. No full conversational chat system in the MVP.
- **Consequences:** Multi-turn chat, digests and alerts are P2 (FR-I14).

### D-016: Profile claim model: basis, review state, uncertainty, missing fields

- **Date:** 2026-11-12
- **Status:** Accepted
- **Context:** The brief asks to "distinguish explicitly stated facts from inferred interests, and flag information that is missing or uncertain", and not to treat inferred interests as confirmed priorities (p.2). A quote found on a page shows only that the source said it when retrieved, not that it is accurate or current. Supersedes D-010.
- **Decision:** `basis` = `stated` | `inferred` | `company_provided`. `review_state` = `unreviewed` | `confirmed` | `rejected` | `superseded`. `uncertain` with a reason. Profile-level `missing_fields`. `is_priority` set only by company action. The UI says "Stated on source", never "Verified".
- **Consequences:** Schemas in [api-contract.md](api-contract.md), tests T-01–T-08.

### D-017: Re-cut P0 for a three-day build

- **Date:** 2026-11-12
- **Status:** Proposed
- **Context:** The verification against the brief added required work (the ask-box with boundaries, flags, next steps, deliverables). Several earlier P0 items were team additions not required by the brief.
- **Decision:** In P0, profiling and collection run from a CLI script; outbound fetching uses an allowlist of member and source domains; opportunity data is a dated snapshot; matching is recomputed synchronously. Moved to P1: admin endpoints, async jobs, arbitrary URLs with full SSRF checks, live refresh with fallback, the offline-demo guarantee, the side-by-side comparison view, PII scrubbing, key-leak scanning. Supersedes the job-execution part of D-009.
- **Consequences:** Less infrastructure. The demo shows pre-run profiling with generation dates, labelled as such.

### D-018: Boundary design: code pre-check, LLM classification, fail closed

- **Date:** 2026-11-12
- **Status:** Proposed
- **Context:** The brief requires reliable boundaries and asks teams to demonstrate them (p.3).
- **Decision:** A deterministic pre-check for override, role-adoption and cross-company patterns; then structured LLM classification into five handling categories; fixed response patterns; post-checks; and a safe remit-and-redirect response on any failure. Details in [security-privacy.md](security-privacy.md#7-interaction-boundaries).
- **Consequences:** Pattern lists need Swedish and English variants. The boundary scenario set in [quality-boundary-check.md](quality-boundary-check.md) is run against the real model before the pitch.

### D-019: Design baseline and simplified P0 frontend scope

- **Date:** 2026-11-12
- **Status:** Accepted (product name and Blue Science Park branding remain pending organiser approval)
- **Context:** Phase 1 and 1.5 design work ([design/](design/)) was reviewed against the brief, the API contract, security rules and the timeline.
- **Decision:**
  - Adopt DD-01 to DD-26 as amended in [design/design-decisions.md](design/design-decisions.md).
  - The P0 frontend is desktop-first (≥ 1280 px), with about 22 reusable components. Mobile responsiveness is P1.
  - The UI uses only fields that exist in [api-contract.md](api-contract.md); no API fields are added (see [design/api-ui-consistency.md](design/api-ui-consistency.md)).
  - Fonts are self-hosted in the application; Google Fonts is never loaded at runtime.
  - Simulated sign-in stays labelled. Company-specific UI and assistant state is cleared on every company switch.
  - No claim of production-grade access isolation is made in the UI or pitch until T-26 and T-30 pass.
- **Consequences:** Phase 2 follows the sequence in [design/prototype-plan.md](design/prototype-plan.md). Organiser-dependent naming and contact routes stay marked as pending verification.

### D-020: Profile completeness excludes inferred relevant topics

- **Date:** 2026-11-12
- **Status:** Accepted (refines the `missing_fields` part of D-016)
- **Context:** `relevant_topic` holds inferred interests by design (brief p.2: "topics and opportunities that may be relevant"). Counting it would make nearly every fresh profile look incomplete, and would blur missing information with inferred interests.
- **Decision:** Completeness covers the six documentable categories. A category counts as documented only when it has an active `stated` or `company_provided` claim. `relevant_topic` is never in `missing_fields`. Inferred-only categories stay missing, and their inferred claims stay labelled as inferred. The UI shows "n of 6 categories documented".
- **Consequences:** FR-P09, FR-U03, T-05, T-09 and T-32 updated. Confirming an inferred claim does not make its category documented; the company documents a category by adding or editing a claim (`company_provided`).

## Pending Decisions

None of the following has been decided.

| Topic | Notes |
|---|---|
| LLM provider and model | Depends on [Q-05](requirements.md#q-open-questions); must support structured output |
| Opportunity sources for the MVP | Proposal: S1 + S3, untested ([sources.md](sources.md)) |
| Demo companies | Real member companies (brief p.1, p.2); which ones and from which list depends on [Q-02](requirements.md#q-open-questions) |
| Staff contact route | Depends on [Q-11](requirements.md#q-open-questions) |
| Topic taxonomy | Fixed tag list used by the Normaliser and Matcher |
| UI language | Depends on [Q-08](requirements.md#q-open-questions) |
| Product name and branding | Team proposal "Virtual Science Park — AI-Powered Innovation Intelligence" (DD-03); use of the name and of Blue Science Park in the UI is **pending organiser approval** |
| Hosting for the demo | Local laptop vs. hosted |
