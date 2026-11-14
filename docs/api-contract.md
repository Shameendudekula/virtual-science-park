# API Contract

**Status:** Proposed (team design; the brief leaves architecture to the team, p.1). No API exists yet. Frontend and backend developers must agree this contract before working in parallel. After that, it changes only by team agreement, with a note in [decisions.md](decisions.md).

- **Style:** REST + JSON, base path `/api/v1`. FastAPI generates the OpenAPI schema from the Pydantic models; this document is the human-readable intent.
- **Conventions:** IDs are strings (UUIDv4, except source IDs). Timestamps are ISO 8601 UTC. Dates without time are `YYYY-MM-DD`. Field names are `snake_case`. A field is nullable only where its type includes `| null`.

## Authentication (simulated in the MVP)

| Header | Grants | Notes |
|---|---|---|
| `X-Company-Token` | One company's private data and actions | Seeded demo token per member. **Simulated sign-in**, labelled in the UI (FR-U01, FR-S06) |

Company-private endpoints return `403 forbidden_company_scope` if the token does not belong to `company_id`. Admin endpoints are P1.

## Endpoints

### P0

| Method | Path | Auth | Purpose | Returns | Requirements |
|---|---|---|---|---|---|
| GET | `/health` | none | Liveness | `{status}` | — |
| GET | `/companies` | none | List demo members (public fields) | `Company[]` | FR-U01 |
| GET | `/companies/{company_id}` | none | Public company fields | `Company` | — |
| GET | `/companies/{company_id}/profile` | company | Profile with claims, evidence and `missing_fields` | `CompanyProfile` | FR-P04–P11, FR-U02, FR-U03 |
| POST | `/companies/{company_id}/profile/claims` | company | Add a claim `{category, value, is_priority?}` → `basis = company_provided` | `201 ProfileClaim` | FR-P12 |
| PATCH | `/companies/{company_id}/profile/claims/{claim_id}` | company | `{action: "confirm" \| "reject" \| "edit" \| "set_priority" \| "unset_priority", value?}`. `edit` returns the new superseding claim | `ProfileClaim` | FR-P10, FR-P12 |
| GET | `/companies/{company_id}/matches?limit=20&type=` | company | Ranked findings; recomputed synchronously if the profile version changed | `Match[]` | FR-M01–M09, FR-U05 |
| POST | `/companies/{company_id}/ask` | company | Ask-box question `{question}`; the server adds the last 3 exchanges of this company | `AssistantResponse` | FR-I01–I12 |
| GET | `/opportunities?type=&source_id=&include_expired=false` | none | Browse collected public items | `Opportunity[]` | FR-O02 |
| GET | `/opportunities/{opportunity_id}` | none | One item | `Opportunity` | — |

Profiling and collection run from a CLI script in P0 (D-017), so they have no endpoints.

### P1

| Method | Path | Purpose | Requirements |
|---|---|---|---|
| POST | `/companies` | Add a company by URL (needs FR-S10) | FR-P17 |
| POST | `/companies/{company_id}/research` | Trigger re-profiling; returns `ResearchJob` | FR-P18 |
| POST | `/opportunities/collect` | Trigger collection; returns `ResearchJob` | FR-O11 |
| GET | `/research-jobs/{job_id}` | Job status | — |
| GET | `/sources` | Source register with last retrieval | FR-O01 |
| POST | `/companies/{company_id}/matches/{match_id}/feedback` | `{value: "relevant" \| "not_relevant"}` (company-private) | FR-M10 |
| POST | `/companies/{company_id}/saved` | Save an item (company-private) | FR-M10 |
| GET | `/companies/{company_id}/interactions` | The company's own question history | FR-I13 |
| GET | `/comparison?company_ids=a,b,c&limit=5` | Opportunity IDs and ranks only; no claims, explanations or interactions | FR-U09 |

### Errors

All errors use one shape:

```json
{ "error": { "code": "forbidden_company_scope", "message": "Token does not grant access to this company", "details": {} } }
```

| HTTP | `code` values |
|---|---|
| 400 | `bad_request`, `question_too_long` |
| 403 | `forbidden_company_scope` |
| 404 | `not_found` |
| 422 | `validation_error`, `invalid_claim_action` (e.g. setting `is_priority` on another company's claim, or `basis = inferred` on `development_project_collaboration`) |
| 502 | `llm_unavailable` (never returned by `/ask`, which fails closed with a safe response) |

## Enums

| Enum | Values |
|---|---|
| `ClaimCategory` | `offering` · `technology_expertise` · `application_area` · `market_customer` · `geographic_focus` · `development_project_collaboration` · `relevant_topic`. These follow the brief, p.2 |
| `ClaimBasis` | `stated`: quote found in the cited source at retrieval time; does not prove current accuracy. `inferred`: AI-derived; has a rationale. `company_provided`: added or edited by the company |
| `ReviewState` | `unreviewed` · `confirmed` · `rejected` · `superseded` |
| `UncertaintyReason` | `third_party_source` · `old_source` · `ambiguous_wording` · `weak_quote_support` · `no_longer_on_source` · `other` |
| `EvidenceSourceType` | `company_website` · `third_party` · `manual` |
| `OpportunityType` | `funding` · `event` · `update` |
| `EventFormat` | `online` · `in_person` · `hybrid` · `unknown` |
| `DataStatus` | `live`: fetched in this run. `snapshot`: stored earlier fetch of a real source. `seed`: curated from a real public source by hand. `simulated`: invented for the demo |
| `HandlingCategory` | `in_scope` · `out_of_scope` · `unclear` · `boundary_override` · `needs_human` |
| `JobKind` | `company_research` · `opportunity_collection` |
| `JobStatus` | `queued` · `running` · `completed` · `failed` |
| `ExplanationMethod` | `llm` · `template` |

## Schemas

✱ = required (non-null).

### Company

| Field | Type | ✱ | Notes |
|---|---|---|---|
| `id` | string | ✱ | |
| `name` | string | ✱ | |
| `website_url` | string (URL) | ✱ | Must be in the fetch allowlist |
| `member_list_source` | string | ✱ | Where the member entry came from ([Q-02](requirements.md#q-open-questions)) |
| `data_status` | `DataStatus` | ✱ | |
| `created_at` | datetime | ✱ | |

**Relationships:** has 1 current `CompanyProfile`, 0..n `ResearchJob`, `Match` and interaction records.

### CompanyProfile

| Field | Type | ✱ | Notes |
|---|---|---|---|
| `id` | string | ✱ | |
| `company_id` | string | ✱ | → `Company` |
| `version` | integer | ✱ | Increments on every change |
| `summary` | string | ✱ | AI-generated; always labelled AI-generated |
| `claims` | `ProfileClaim[]` | ✱ | Includes rejected and superseded claims (the UI hides them by default) |
| `missing_fields` | `ClaimCategory[]` | ✱ | Documentable categories (all except `relevant_topic`) without an active `stated` or `company_provided` claim (FR-P09). Never contains `relevant_topic`. The UI shows completeness as 6 − length |
| `last_researched_at` | datetime | ✱ | Time of the profiling run |
| `updated_at` | datetime | ✱ | Time of the last change |
| `data_status` | `DataStatus` | ✱ | |

### ProfileClaim

| Field | Type | ✱ | Notes |
|---|---|---|---|
| `id` | string | ✱ | |
| `profile_id` | string | ✱ | → `CompanyProfile` |
| `category` | `ClaimCategory` | ✱ | |
| `value` | string | ✱ | |
| `basis` | `ClaimBasis` | ✱ | Set by the Evidence Checker or the user action, never directly by LLM output |
| `review_state` | `ReviewState` | ✱ | Starts `unreviewed` (system claims) or `confirmed` (company-provided) |
| `is_priority` | boolean | ✱ | Default `false`; set only by company action (FR-P10) |
| `uncertain` | boolean | ✱ | |
| `uncertainty_reason` | `UncertaintyReason` \| null | | Required when `uncertain = true` |
| `inference_rationale` | string \| null | | Required when `basis = inferred` |
| `evidence` | `Evidence[]` | ✱ | ≥1 with `quote_found = true` when `basis = stated` |
| `supersedes_claim_id` | string \| null | | Set on a company edit |
| `created_by` | `"system"` \| `"company"` | ✱ | |
| `created_at` | datetime | ✱ | |

**Invariants:**
- `basis = stated` ⇒ ≥1 evidence item with `quote_found = true`.
- `category = development_project_collaboration` ⇒ `basis` is not `inferred`.
- `is_priority = true` ⇒ set by company action.
- Claims with `review_state` `rejected` or `superseded` are never used for matching or by the assistant.

### Evidence

| Field | Type | ✱ | Notes |
|---|---|---|---|
| `id` | string | ✱ | |
| `claim_id` | string | ✱ | → `ProfileClaim` |
| `source_type` | `EvidenceSourceType` | ✱ | |
| `source_url` | string (URL) | ✱ | |
| `page_title` | string \| null | | |
| `quote` | string (≤ 500 chars) | ✱ | |
| `quote_found` | boolean | ✱ | Result of the Evidence Checker |
| `retrieved_at` | datetime | ✱ | |
| `source_published_at` | date \| null | | Page date, if detectable |
| `content_hash` | string | ✱ | SHA-256 of the stored page text |

### Opportunity

**Common fields:**

| Field | Type | ✱ | Notes |
|---|---|---|---|
| `id` | string | ✱ | |
| `source_id` | string | ✱ | → [sources.md](sources.md) |
| `source_name` | string | ✱ | |
| `external_id` | string \| null | | |
| `type` | `OpportunityType` | ✱ | |
| `title` | string | ✱ | |
| `summary` | string | ✱ | ≤ 1,000 chars |
| `source_url` | string (URL) | ✱ | |
| `retrieved_at` | datetime | ✱ | |
| `data_status` | `DataStatus` | ✱ | |
| `date_unknown` | boolean | ✱ | `true` if no relevant date could be found (FR-O08) |
| `expired` | boolean | ✱ | Deadline or end date has passed (FR-O09) |
| `tags` | string[] | ✱ | Topic-taxonomy tags |
| `language` | `"sv"` \| `"en"` \| `"other"` | ✱ | |

**Funding fields** (`type = funding`; required keys, values may be null meaning "not stated in source"):

| Field | Type | Notes |
|---|---|---|
| `funder` | string \| null | |
| `purpose` | string \| null | Brief p.3 item 4 |
| `deadline` | date \| null | |
| `eligibility_summary` | string \| null | Key eligibility requirements as stated by the source; not an assessment |

**Event fields** (`type = event`):

| Field | Type | Notes |
|---|---|---|
| `format` | `EventFormat` | Brief p.3 item 2 |
| `audience` | string \| null | "Who it's for" |
| `starts_at` | datetime \| null | |
| `ends_at` | datetime \| null | |
| `location` | string \| null | |
| `organiser` | string \| null | |

**Update fields** (`type = update`):

| Field | Type | Notes |
|---|---|---|
| `published_at` | date \| null | |
| `what_changed` | string \| null | Brief p.2 item 1 |

### Match

| Field | Type | ✱ | Notes |
|---|---|---|---|
| `id` | string | ✱ | |
| `company_id` | string | ✱ | → `Company` |
| `opportunity` | `Opportunity` | ✱ | Embedded |
| `score` | number 0.0–1.0 | ✱ | Deterministic (FR-M09) |
| `rank` | integer ≥ 1 | ✱ | |
| `explanation` | string | ✱ | Why it is relevant; for updates, why the change could matter (FR-M04) |
| `explanation_method` | `ExplanationMethod` | ✱ | |
| `supporting_claim_ids` | string[] (≥1) | ✱ | → `ProfileClaim` of the same company |
| `matched_terms` | string[] | ✱ | |
| `next_step` | string | ✱ | A possible next step; never a commitment (FR-M05) |
| `match_label` | string \| null | | `"Potential match — eligibility not assessed"` for funding (FR-M06) |
| `uncertainties` | string[] | ✱ | e.g. "Deadline not stated in source"; may be empty |
| `disclaimer` | string | ✱ | [security-privacy.md](security-privacy.md#honesty-rules) |
| `profile_version` | integer | ✱ | |
| `computed_at` | datetime | ✱ | |

### AssistantResponse

| Field | Type | ✱ | Notes |
|---|---|---|---|
| `handling` | `HandlingCategory` | ✱ | Shown in the UI (FR-I02) |
| `answer` | string | ✱ | Answer, remit statement, clarifying question or referral text |
| `citations` | `{title: string, url: string}[]` | ✱ | Only URLs already stored for this company's context or public items |
| `suggested_questions` | string[] | ✱ | For `out_of_scope` and `unclear`; may be empty otherwise |
| `referral` | `{to: "Blue Science Park staff", route: string \| null, route_status: "verified" \| "pending_verification"}` \| null | | Set for `needs_human` (FR-I08) |
| `disclaimer` | string \| null | | Present when the answer discusses opportunities |
| `interaction_id` | string | ✱ | Company-private record |

**Internal (not exposed in P0):** `Interaction {id, company_id, question, handling, answer, created_at}`. These records are company-private (FR-S06).

### ResearchJob

Run record for profiling and collection. Created by the CLI in P0; via endpoints in P1.

| Field | Type | ✱ | Notes |
|---|---|---|---|
| `id` | string | ✱ | |
| `kind` | `JobKind` | ✱ | |
| `status` | `JobStatus` | ✱ | |
| `company_id` | string \| null | | For `company_research` |
| `source_ids` | string[] | ✱ | For `opportunity_collection`; otherwise empty |
| `pages_fetched` | integer | ✱ | |
| `items_created` | integer | ✱ | |
| `warnings` | string[] | ✱ | |
| `error` | `{code, message}` \| null | | |
| `started_at` | datetime | ✱ | |
| `finished_at` | datetime \| null | | |

### Source (P1 endpoint; P0 configuration file)

| Field | Type | ✱ | Notes |
|---|---|---|---|
| `id` | string | ✱ | e.g. `vinnova` |
| `name` | string | ✱ | |
| `base_url` | string (URL) | ✱ | |
| `access_method` | `"api"` \| `"html"` \| `"feed"` \| `"file"` | ✱ | Recorded only after testing ([sources.md](sources.md)) |
| `opportunity_types` | `OpportunityType[]` | ✱ | |
| `last_retrieved_at` | datetime \| null | | |

## Relationships

```text
Company 1 ── 1 CompanyProfile 1 ── * ProfileClaim 1 ── * Evidence ──> SourceDocument (internal)
Company 1 ── * Match * ── 1 Opportunity * ── 1 Source
Match * ── 1..* ProfileClaim   (supporting_claim_ids)
Company 1 ── * Interaction (private)      Company 1 ── * ResearchJob
```

## To Be Agreed Before Parallel Work

- [ ] P0 endpoint list and auth header
- [ ] Enum values (especially `ClaimCategory`, `ClaimBasis`, `HandlingCategory`)
- [ ] Required fields of ProfileClaim, Opportunity (per type), Match, AssistantResponse
- [ ] Error codes
- [ ] Mock JSON for the frontend in `data/mock/` (one file per schema, labelled `simulated`)

## Implementation Notes (Phase 2, 2026-11-13)

Changes made while implementing the backend. All are additive except the new `401`, and each has a reason.

| Change | Reason |
|---|---|
| `401 unauthenticated` when `X-Company-Token` is missing (403 remains for a token of another company) | Distinguish "not signed in" from "wrong company" |
| `ReviewState` adds `outdated`; PATCH action `mark_outdated` | Lets a company mark a claim as no longer true without calling it wrong; kept for history |
| `GET /companies/{id}/matches/{match_id}` | Finding detail and deep links (closes design gap DD-12); match IDs are stable per company + opportunity |
| `GET /companies/{id}/profile/revisions` | Revision history of company refinements |
| `GET /companies/{id}/collaborations` | Stage 4: company-to-company collaboration suggestions (partner side uses only public, source-stated claims) |
| `GET /companies/{id}/topics` | Stage 3: technology topics the company states, and topics to explore found in matched opportunities |
| `GET /sources` moved to P0 | Source health is needed to show retrieval status honestly |
| Match adds `level` (`strong` / `potential` / `limited`), `level_label`, `points`, `reasons`, `supporting_claims`, `evidence`, `missing` | Explainability: every match states why, which claims, which quotes, and what is unknown. `score` stays as `min(points / 5, 1)` and is a ranking aid, not a probability |
| Profile adds `completeness` (`{documented, total: 6}`) and `summary_source` | FR-P09 display; the summary is quoted from the company's homepage meta description, not generated |
| Claim adds `rule_id`; Company adds `membership_evidence_url`, `membership_verified_at` | Transparency of extraction rules and of membership verification |
| Opportunity adds `expired` (computed) and `source_name` | FR-O09 and display |

Not yet implemented: `POST /companies/{id}/ask` (assistant, next phase) and the P1 endpoints.
