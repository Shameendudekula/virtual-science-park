# Architecture

**Status:** Proposed. Nothing is implemented. The brief leaves tools and architecture to the team (p.1 Scope), so everything in section 2 is a **team proposal** (decisions D-005 onwards in [decisions.md](decisions.md)).

This document has three parts:

1. **Official constraints** from the brief.
2. **Team-proposed architecture.**
3. **Open design questions.**

---

## 1. Official Constraints

From the brief (see [research/challenge-analysis.md](research/challenge-analysis.md) for page references):

- One working flow from member discovery to a personalised result, starting from a member list (BR-02; p.1, p.2).
- Baseline profiles for at least three members, with evidence, source links and retrieval dates; stated facts separated from inferred interests; missing and uncertain information flagged; no inferred priorities or confidential plans (BR-03–BR-08; p.1, p.2).
- Users can review and refine profiles (BR-09; p.1).
- Opportunities or updates from at least two distinct public sources; different results for different profiles; source links and relevant dates (BR-10–BR-12; p.1).
- Interaction boundaries: relevant, unrelated and override requests; follow-ups; unclear requests; human referral; no disclosure of other companies' non-public data or interactions; external content as data (BR-13, BR-16–BR-22; p.1, p.3).
- Simulated data and functionality labelled (BR-14; p.1).
- **Explain the roles of the agents and how they work together** (p.1), and **how it would scale** to 40+ members (p.1). Both are explained here and in [solution-overview.md](solution-overview.md).

---

## 2. Team-Proposed Architecture

### Principles

- **Modular monolith.** One FastAPI process, one React frontend, one SQLite file. No microservices, queues or distributed workers (D-009, D-017).
- **Agents propose, code decides.** LLM-based agents draft claims, explanations and answers. Code validates evidence, computes scores, enforces scope and access, and appends disclaimers.
- **Provenance on every record.** Source URL, `retrieved_at` and `data_status` are required fields.
- **Synchronous and scripted in the MVP.** Profiling and collection run from a command-line script for the demo members and store their results. Matching is recomputed synchronously when a profile changes (D-017).

### Agents and how they work together

"Agent" means a backend module with a single responsibility. Some agents call an LLM through the LLM Gateway; none of them has tool access.

| Agent | Role | LLM | Input → Output | Requirements |
|---|---|---|---|---|
| **Profiling agent** | Builds baseline profiles from the member list | Yes (extraction) | Member list → fetched pages → draft claims → validated `CompanyProfile` | FR-P01–P13 |
| ↳ SafeFetcher | Fetches allowlisted pages, visible text only, `robots.txt`, limits | No | URL → `SourceDocument` | FR-P02, FR-P03, FR-S04, FR-S05 |
| ↳ Profile Extractor | Drafts claims in the brief's categories, with quotes or rationale | Yes | Delimited page text → draft claims | FR-P04, FR-P07, FR-S01–S03 |
| ↳ Evidence Checker | Sets `basis` (`stated` only if the quote is found), applies `uncertain` flags, computes `missing_fields`, enforces FR-P11 | No | Draft claims + pages → claims | FR-P05, FR-P06, FR-P08, FR-P09, FR-P11 |
| **Monitoring agents** | Collect funding, events and updates from public sources | Optional (field extraction) | Source → raw items → `Opportunity` snapshot | FR-O01–O09 |
| ↳ Funding collector | Funding calls (S1 in [sources.md](sources.md)) | Optional | → `type = funding` with purpose, deadline, eligibility summary | FR-O05 |
| ↳ Events & updates collector | Events and news (S3) | Optional | → `type = event` / `update` | FR-O06, FR-O07 |
| ↳ Normaliser | Validates provenance, tags topics, flags expired items and unknown dates | No | Raw → `Opportunity` | FR-O02–O04, FR-O08, FR-O09 |
| **Matching agent** | Ranks findings per company and explains them | Yes (explanations only) | Active claims + items → `Match[]` | FR-M01–M09 |
| ↳ Matcher | Deterministic score from tag overlap and keyword similarity, weighted by claim basis and priority | No | → score, rank, supporting claims | FR-M01–M03, FR-M09 |
| ↳ Explainer | Writes "why relevant" from cited claims and item text; template fallback | Yes | → explanation | FR-M04, FR-M08 |
| ↳ Next-step and disclaimer builder | Per-type next step, funding "potential match" label, disclaimer, banned-phrase check | No | → `next_step`, labels, disclaimer | FR-M05–M07 |
| **Assistant** | Answers ask-box questions within the service's purpose | Yes | Question + company context → `AssistantResponse` | FR-I01–I12 |
| ↳ Scope Guard | Deterministic pre-checks, then LLM classification; fails closed | Yes | → handling category | FR-I02, FR-I06, FR-I10, FR-I12 |
| ↳ Responder | Grounded answer, remit/redirect, clarifying question, or staff referral | Yes | → answer + citations | FR-I03–FR-I05, FR-I08, FR-I09 |

**How they work together.** Agents don't call each other directly. They communicate through stored records:

```text
Member list ─► [Profiling agent] ─► CompanyProfile ─► (user review / refine) ─┐
                                                                               ├─► [Matching agent] ─► Match[] ─► Dashboard
Public sources ─► [Monitoring agents] ─► Opportunity snapshots ───────────────┘
                                                                                         │
User question ─► [Assistant: Scope Guard ─► Responder] ◄── reads active company's profile, matches, public items
```

### Pipeline

```text
 Member list (config)                          Public sources (untrusted)
        │                                               │
 [1] Public information collection            [5] Opportunity / update collection
     SafeFetcher (allowlist, visible text)        Funding collector, Events & updates collector
        │                                               │  dated snapshot
 [2] Company profile extraction               [6] Normalisation
     LLM, brief categories, no tools              provenance, type fields, expiry, tags
        │                                               │
 [3] Evidence check (code)                              │
     stated / inferred, uncertain, missing_fields       │
        │                                               │
 [4] Company profile review                             │
     confirm / reject / edit / add / priority           │
        └─────────────────────┬─────────────────────────┘
                              ▼
                   [7] Matching and ranking (code score + LLM explanation + next step)
                              ▼
                   [8] Personalised dashboard + ask-box (frontend)
```

### Claim model (D-016)

| Dimension | Values | Set by |
|---|---|---|
| `basis` | `stated` (quote found in cited source) · `inferred` (AI-derived, with rationale) · `company_provided` | Evidence Checker / user action |
| `review_state` | `unreviewed` · `confirmed` · `rejected` · `superseded` | User action |
| `is_priority` | `true` only through user action | User action |
| `uncertain` + `uncertainty_reason` | e.g. `third_party_source`, `old_source`, `ambiguous_wording`, `weak_quote_support` | Evidence Checker (and Extractor suggestion) |
| `missing_fields` (profile level) | Documentable categories (all except `relevant_topic`) with no active stated or company-provided claim; inferred-only categories stay missing (FR-P09, D-020) | Evidence Checker |

`stated` means "the source said this when retrieved". It is not a claim of accuracy, which is why the UI says "Stated on source", not "Verified".

### Matching method (D-011)

- **Score:** a weighted sum of (a) topic-tag overlap between active claims and the item, using a small fixed taxonomy, and (b) TF-IDF keyword similarity. Claim weights follow FR-M03: priority > company-provided/confirmed > stated > inferred. Expired items are excluded.
- **Supporting claims:** the top-contributing claims. The explanation must cite them.
- **Explanation:** the LLM sees only the cited claims and the item text. Inferred claims must be phrased as "may be relevant" (FR-M08). On failure, a template is used.
- **Next step and labels:** built by code per type. Funding matches always get "Potential match — eligibility not assessed".

### Assistant and boundaries

Detailed rules: [security-privacy.md §7](security-privacy.md#7-interaction-boundaries).

1. **Pre-checks (code):** length limit; patterns for override and role-adoption attempts; mentions of other demo companies' names combined with private-data terms.
2. **Classification (LLM, structured output):** `in_scope`, `out_of_scope`, `unclear`, `boundary_override` or `needs_human`. Pre-check hits take precedence.
3. **Response:**
   - `in_scope`: answer only from the active company's context, with citations.
   - `out_of_scope`: remit statement plus suggestion.
   - `unclear`: one clarifying question.
   - `boundary_override`: decline and restate the remit.
   - `needs_human`: staff referral.
4. **Post-checks (code):** response schema, banned phrases, citations limited to known URLs, disclaimer where needed.
5. **Fail closed:** any error returns the standard remit-and-redirect response (FR-I12).

Follow-ups: the last 3 exchanges of the active company session are included as context, and steps 1–4 run on every turn.

### Frontend and backend responsibilities

| Frontend (React, TypeScript, Vite, Tailwind) | Backend (FastAPI, Pydantic, SQLite) |
|---|---|
| Company selector (simulated sign-in), profile review, missing-info panel, findings dashboard, ask-box | Fetching, LLM calls, evidence checks, scoring, scope guard, persistence |
| Renders the badges, labels, dates, next steps, disclaimers and demo banner it receives | Decides every status, label and handling category; the frontend never infers trust |
| Accessible markup (FR-U08) | Enforces company scope on every company-private endpoint |
| Never calls external sources or the LLM directly | Holds API keys |

### Data and storage

The SQLite tables mirror [api-contract.md](api-contract.md): `companies`, `source_documents`, `company_profiles`, `profile_claims`, `evidence`, `sources`, `opportunities`, `matches`, `interactions` (company-private), `research_jobs`, `llm_cache`.

- Member list and source configuration live in `data/config/`.
- Collected snapshots live in `data/snapshots/`, with retrieval dates.
- The database file and raw HTML cache are gitignored.

### Trust boundaries

| Boundary | What crosses it | Treated as | Controls |
|---|---|---|---|
| Internet → SafeFetcher / collectors | Pages, feeds, API responses | **Untrusted** | Allowlist (FR-S04), limits, visible text only (FR-S05) |
| Stored text → LLM | Page and item text | **Untrusted data** | Delimiters, data-only rule, no tools (FR-S01, FR-S02) |
| LLM → database / UI | Claims, explanations, answers | **Untrusted output** | Schema validation, Evidence Checker, banned phrases, citation check (FR-S03) |
| Browser → API | Questions, edits, company ID, token | **Untrusted input** | Request validation, company scope (FR-S06), Scope Guard |
| Backend → LLM provider | Public text and the active company's own context | **External processor** | No other company's data (FR-S07); pending [Q-05](requirements.md#q-open-questions) |

### Failure handling

| Failure | Behaviour |
|---|---|
| Member site unreachable or disallowed by `robots.txt` | Run recorded with warnings; profile built from the pages that worked; affected categories appear in `missing_fields` |
| LLM error or invalid output during profiling | One retry, then the run fails; the previous profile is kept |
| Quote not found | Claim becomes `inferred` (not dropped), except `development_project_collaboration` claims, which are dropped (FR-P11) |
| Source collector fails | Previous snapshot stays in use, labelled with its original `retrieved_at` |
| Explainer fails or uses a banned phrase | Template explanation |
| Assistant error or invalid output | Fail-closed remit-and-redirect response (FR-I12) |

### MVP architecture (P0) vs deferred

| P0 | Deferred |
|---|---|
| CLI script runs profiling and collection for the demo members and sources | Admin endpoints and async jobs (P1) |
| Fetch allowlist (member and source domains) | Arbitrary URLs with full SSRF checks (P1, FR-S10) |
| Dated snapshots | Live refresh with fallback (P1), scheduled refresh (P2) |
| Deterministic matching, synchronous recompute | Feedback-based ranking, embeddings (P2) |
| Ask-box with scope guard | Multi-turn chat, digests, alerts (P2) |
| Simulated per-company sign-in | Real authentication |
| SQLite and SQLAlchemy, database rebuilt by script | Alembic, Postgres |

### Keeping profiles current (explained, not built: P2)

- **Re-profiling cadence:** re-run the profiling agent per member on a schedule (e.g. monthly), and on demand when a member asks.
- **Change detection:** compare page content hashes; only changed pages are re-extracted, and LLM results are cached by content hash.
- **Claim diff (FR-P19):**
  - New claims arrive as `unreviewed`.
  - A claim whose quote has disappeared is flagged `uncertain` (`no_longer_on_source`).
  - `company_provided` claims and company decisions are never overwritten.
- **Member updates:** public news and press pages of members are monitored like any source; matching items can suggest profile updates for the company to accept.
- **Visibility:** each profile shows its last-researched date, and the company is prompted to review when new claims arrive.

### Scaling to 40+ members (explained, not built)

- **Volume:** 40+ members × ~10 pages is a few hundred page fetches per full refresh. A single process with per-host rate limits can handle this as a background batch. Actual run time and cost will be measured on the demo set and extrapolated in [solution-overview.md](solution-overview.md); no figures are claimed yet.
- **Changes:**
  - Move from CLI runs to a job queue with scheduled workers.
  - SQLite → Postgres for concurrent users.
  - Real sign-in (organisation accounts) instead of simulated tokens.
  - Staff view of shared interests across members (FR-U12).
- **Unchanged:** the agent roles, the claim model, the matching interface and the boundary design all work the same per member.
- **Onboarding:** the member list file becomes a staff-managed list; each new member gets a baseline profile and a review invitation.

### Extension points

- Add a source collector (one module plus an entry in [sources.md](sources.md)).
- Testing-opportunity area (FR-O13).
- Collaboration suggestions between members, with no assumed interest (FR-M12).
- Embedding or hybrid ranking behind the Matcher interface (FR-M13).
- Swap the LLM provider in the gateway, or use a local model (Q-05).
- Digests and alerts (FR-I14).

---

## 3. Open Design Questions

Questions for the organisers: [requirements.md, section Q](requirements.md#q-open-questions). Pending team decisions: [decisions.md](decisions.md#pending-decisions).
