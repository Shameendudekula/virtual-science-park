# Requirements

**Status:** Draft, revised after verification against the official brief (2026-11-12). Pending team approval.
**Authority:** The official challenge brief (4 pages), summarised with page references in [research/challenge-analysis.md](research/challenge-analysis.md). Use cases: [research/use-cases.md](research/use-cases.md).

This document is the **single source of truth for priorities**. Other documents link here instead of restating priorities.

## Conventions

| Column | Values |
|---|---|
| **Origin** | **Official**: stated in the brief; the **PDF** column gives page and section. **Official / Team**: the brief states the need, and the acceptance criterion is ours. **Team**: our design proposal; not required by the brief. |
| **PDF** | Page and section in the brief, e.g. *p.1 Scope*, *p.3 Boundaries* (= "Keep interactions within the service's purpose"). |
| **Priority** | **P0**: critical MVP for the demo. **P1**: should have. **P2**: could have / future work. |
| **Test** | Test IDs in [testing.md](testing.md). "Demo" = checked in the demo script. "—" = no test yet. |

---

## BR: Business Requirements (Official)

Each BR restates a requirement from the brief. The FR and NFR sections describe how we plan to meet them.

| ID | Requirement | PDF | Priority |
|---|---|---|---|
| BR-01 | Use AI agents to understand member companies, identify relevant information and opportunities, and present results through a clear interface | p.1 The challenge | P0 |
| BR-02 | Build one working flow from member discovery to a personalised result, starting from a member list | p.1 Scope; p.2 Start by understanding the members | P0 |
| BR-03 | Generate baseline profiles for at least three member companies from their websites and other public sources where available | p.1 Scope (bullet 1) | P0 (websites), P1 (other sources) |
| BR-04 | Profiles cover: offering; technologies, expertise and application areas; markets, industries and customer groups; geographical focus where stated; publicly stated development priorities, projects and collaborations; potentially relevant topics | p.2 Start by understanding the members | P0 |
| BR-05 | Show the evidence behind profile information, and distinguish explicitly stated facts from inferred interests | p.1 Scope (bullet 2); p.2 | P0 |
| BR-06 | Each profile includes source links and the date the information was retrieved | p.2 | P0 |
| BR-07 | Flag information that is missing or uncertain | p.2 | P0 |
| BR-08 | Don't infer confidential plans, and don't treat an inferred interest as a confirmed company priority | p.2 | P0 |
| BR-09 | Let a user review and refine a profile | p.1 Scope (bullet 3); p.4 Example journey (step 2) | P0 |
| BR-10 | Collect opportunities or updates from at least two distinct public information sources | p.1 Scope (bullet 4) | P0 |
| BR-11 | Show different recommendations or rankings for companies with different profiles | p.1 Scope (bullet 5) | P0 |
| BR-12 | Present results with source links and relevant dates | p.1 Scope (bullet 6) | P0 |
| BR-13 | Respond appropriately to a relevant request, an unrelated request and an attempt to override the service's boundaries | p.1 Scope (bullet 7); p.3 Boundaries | P0 |
| BR-14 | Clearly label simulated data or functionality | p.1 Scope (bullet 8) | P0 |
| BR-15 | Choose one or two monitoring areas and demonstrate them convincingly (team choice: D-014) | p.1 Scope | P0 |
| BR-16 | Keep all interactions within the service's purpose: innovation, business development and collaboration within the science park ecosystem, using the five supported interaction types | p.1 The challenge; p.3 Boundaries | P0 |
| BR-17 | Treat external websites and documents as information sources, never as instructions that can change the service's role or rules | p.3 Boundaries | P0 |
| BR-18 | Apply the same boundaries to follow-up questions and to requests to adopt another role | p.3 Boundaries | P0 |
| BR-19 | Never disclose another company's non-public profile information or user interactions | p.3 Boundaries | P0 |
| BR-20 | Distinguish information and suggested next steps from professional advice, formal eligibility decisions or commitments by Blue Science Park; distinguish a potential funding match from confirmed eligibility | p.3 Boundaries; p.3 item 4 Funding | P0 |
| BR-21 | Refer questions that need a human decision or commitment to Blue Science Park staff | p.3 Boundaries | P0 |
| BR-22 | For out-of-scope requests, briefly explain the remit and guide towards a relevant question or the right contact. For unclear requests, ask a focused clarifying question | p.3 Boundaries | P0 |
| BR-23 | Accessible interface in which users can verify the source, understand the relevance and see a possible next step | p.3 item 6 Presentation and interaction | P0 |
| BR-24 | Funding: summarise purpose, deadlines and key eligibility requirements | p.3 item 4 Funding | P0 (selected area) |
| BR-25 | Events: show whether online or in person, who they're for and key dates | p.3 item 2 Events | P0 (selected area) |
| BR-26 | Knowledge and trend updates: explain what has changed and why it could matter to the company | p.2 item 1 Knowledge and trend monitoring | P0 (selected area; see the cut rule in D-014) |

Brief items that are **not** in our MVP: testing opportunities (p.3 item 3), member-update monitoring and collaboration suggestions (p.3 item 5), staff view of shared interests (p.2). The brief does not require these for the hackathon (p.1 "choose one or two"). They appear below as P1/P2.

## DLV: Deliverables (Official)

| ID | Deliverable | PDF | Document | Priority |
|---|---|---|---|---|
| DLV-01 | Working demo showing company profiling, profile refinement and personalised findings | p.1 What to deliver | [pitch-outline.md](pitch-outline.md) | P0 |
| DLV-02 | Short explanation of the solution: sources, agent roles, matching, how profiles stay current; plus how it would scale to 40+ members and how the agents work together | p.1 Scope; p.2 What to deliver | [solution-overview.md](solution-overview.md) | P0 |
| DLV-03 | Quality and boundary check: profile accuracy, recommendation relevance, source traceability, interaction limits; explain and demonstrate how the boundaries are implemented | p.2 What to deliver; p.3 Boundaries (last line) | [quality-boundary-check.md](quality-boundary-check.md) | P0 |
| DLV-04 | Handover: code, setup instructions, known limitations, suggested next steps | p.2 What to deliver | [handover.md](handover.md) | P0 |
| DLV-05 | Pitch: the problem, a demo of the solution, the value to a company, what to develop next | p.2 What to deliver | [pitch-outline.md](pitch-outline.md) | P0 |

---

## FR-P: Company Profile Requirements

| ID | Requirement (acceptance criterion) | Origin | PDF | Meets | Use case | Priority | Test |
|---|---|---|---|---|---|---|---|
| FR-P01 | Profiling starts from a member list file (company name, website) for the selected demo members; outbound fetching is limited to these domains (FR-S04) | Official / Team | p.2 | BR-02 | UC-01 | P0 | T-09 |
| FR-P02 | The profiling agent fetches each member's homepage and up to 10 same-site pages, respects `robots.txt`, and records URL and `retrieved_at` per page | Official / Team | p.1 Scope; p.2 | BR-03, BR-06 | UC-01 | P0 | T-02 |
| FR-P03 | Fetched pages are stored as source documents with URL, `retrieved_at`, page published/modified date when detectable, visible text and content hash | Team | — | BR-06 | UC-01 | P0 | T-02 |
| FR-P04 | Claims are extracted into the brief's categories: `offering`, `technology_expertise`, `application_area`, `market_customer`, `geographic_focus`, `development_project_collaboration`, `relevant_topic` | Official | p.2 | BR-04 | UC-01, UC-02 | P0 | T-09 |
| FR-P05 | Every claim has one `basis`: `stated`, `inferred` or `company_provided`. A `stated` claim has at least one evidence item with quote, source URL and `retrieved_at` | Official / Team | p.1 Scope; p.2 | BR-05, BR-06 | UC-02 | P0 | T-02 |
| FR-P06 | A claim is `stated` only if its quote is found in the stored text of the cited page (whitespace and case normalised); otherwise it becomes `inferred`. A found quote proves only that the source said it at retrieval time, not that it is accurate or current | Team | — | BR-05 | UC-02 | P0 | T-01 |
| FR-P07 | Every `inferred` claim has a short rationale | Team | — | BR-05 | UC-02 | P0 | T-02 |
| FR-P08 | A claim can be flagged `uncertain` with a reason, e.g. `third_party_source`, `old_source`, `ambiguous_wording`, `weak_quote_support` | Official / Team | p.2 | BR-07 | UC-02 | P0 | T-06 |
| FR-P09 | The profile lists `missing_fields`: those of the six **documentable** categories (`offering`, `technology_expertise`, `application_area`, `market_customer`, `geographic_focus`, `development_project_collaboration`) that have no active (not rejected or superseded) claim with `basis` `stated` or `company_provided`. `relevant_topic` is excluded and never reported as missing, because it holds inferred interests by design. A documentable category whose only active claims are `inferred` stays in `missing_fields`, and those claims keep their `inferred` label (missing information and inferred interests stay distinct). Completeness is shown as "n of 6 categories documented" (D-020) | Official / Team | p.2 | BR-07, BR-08 | UC-02 | P0 | T-05 |
| FR-P10 | Only company action sets `is_priority`. AI-generated claims are never marked or described as priorities | Official / Team | p.2 | BR-08 | UC-03 | P0 | T-07 |
| FR-P11 | `development_project_collaboration` claims must be `stated` (quote found) or `company_provided`, never `inferred`. Extraction uses public pages only | Official / Team | p.2 | BR-08 | UC-01 | P0 | T-08 |
| FR-P12 | A user can confirm, reject, edit or add a claim, and set or unset priority. An edit creates a `company_provided` claim with `supersedes_claim_id`; the original is kept as `superseded` | Official / Team | p.1 Scope; p.4 step 2 | BR-09 | UC-03 | P0 | T-03 |
| FR-P13 | At least three member profiles are generated by the profiling agent from public sources. No hand-written content is presented as AI-generated. Cached profiles show their generation date | Official / Team | p.1 Scope | BR-03, BR-14 | UC-01 | P0 | T-09 |
| FR-P14 | Profile version history | Team | — | BR-09 | UC-03 | P1 | — |
| FR-P15 | Research public sources other than the website, where available (e.g. press releases, public registries) | Official | p.1 Scope; p.2 | BR-03 | UC-16 | P1 | — |
| FR-P16 | Admin can supply public text or URLs manually when a site cannot be fetched; such evidence is labelled `manual` | Team | — | BR-03, BR-14 | UC-01 | P1 | — |
| FR-P17 | Add a new company by arbitrary URL (requires FR-S10) | Team | — | BR-02 | UC-17 | P1 | — |
| FR-P18 | Scheduled re-profiling and monitoring of public member updates to keep profiles current | Official (area 5, not selected) | p.3 item 5 | BR-02 | UC-16 | P2 | — |
| FR-P19 | On re-profiling, diff claims: new claims start `unreviewed`; claims whose quote has disappeared are flagged `uncertain` (`no_longer_on_source`); `company_provided` claims are never overwritten | Team | — | BR-07, BR-09 | UC-16 | P2 | — |

## FR-O: Opportunity and Update Discovery Requirements

Selected areas (D-014): **funding**, **events**, **knowledge/trend updates**.

| ID | Requirement (acceptance criterion) | Origin | PDF | Meets | Use case | Priority | Test |
|---|---|---|---|---|---|---|---|
| FR-O01 | Collectors exist for at least two distinct public sources from [sources.md](sources.md), covering funding plus events and/or updates | Official / Team | p.1 Scope | BR-10, BR-15 | UC-04, UC-05 | P0 | T-11 |
| FR-O02 | Every item is normalised to the `Opportunity` schema and has `source_url`, `retrieved_at`, `data_status`, `type`, `title` and `summary`; records without these are rejected | Official / Team | p.1 Scope | BR-12 | UC-04, UC-05 | P0 | T-10 |
| FR-O03 | `data_status` is `live`, `snapshot`, `seed` or `simulated`, and is shown wherever the item appears | Official / Team | p.1 Scope | BR-14 | UC-06 | P0 | T-10, T-31 |
| FR-O04 | `type` is one of `funding`, `event`, `update` | Team | — | BR-15 | UC-04, UC-05 | P0 | T-11 |
| FR-O05 | Funding items have `purpose`, `deadline` and `eligibility_summary` (taken from the source text), plus `funder`. A value missing from the source is shown as "not stated in source", never guessed | Official / Team | p.3 item 4 | BR-24 | UC-04 | P0 | T-12 |
| FR-O06 | Event items have `format` (`online`, `in_person`, `hybrid`, `unknown`), `audience`, `starts_at`, `ends_at` and `location`. Unknown values are labelled as such | Official / Team | p.3 item 2 | BR-25 | UC-05 | P0 | T-13 |
| FR-O07 | Update items have `published_at` and `what_changed` (a short summary from the source) | Official / Team | p.2 item 1 | BR-26 | UC-05 | P0 | T-14 |
| FR-O08 | Every item has at least one relevant date (`deadline`, `starts_at` or `published_at`), or `date_unknown = true` | Official / Team | p.1 Scope | BR-12 | UC-06 | P0 | T-14 |
| FR-O09 | Items whose deadline or end date has passed are flagged `expired` and excluded from matching | Team | — | BR-12 | UC-06 | P0 | T-14 |
| FR-O10 | De-duplicate items within a source (same external ID or URL) | Team | — | BR-10 | UC-04 | P1 | — |
| FR-O11 | Live re-fetch on demand with automatic snapshot fallback. In P0, collectors run once and store a dated `snapshot` | Team | — | BR-10, BR-14 | UC-04 | P1 | — |
| FR-O12 | Scheduled collection | Team | — | BR-10 | UC-16 | P2 | — |
| FR-O13 | Testing-opportunity area (testbeds, labs, demonstration environments, pilots, with next step) | Official (area 3, not selected) | p.3 item 3 | BR-15 | UC-19 | P2 | — |

## FR-M: Matching Requirements

| ID | Requirement (acceptance criterion) | Origin | PDF | Meets | Use case | Priority | Test |
|---|---|---|---|---|---|---|---|
| FR-M01 | For each company, rank non-expired items with a `score` from 0.0 to 1.0 and a `rank` | Official / Team | p.1 Scope; p.3 item 5 | BR-11 | UC-06 | P0 | T-15, T-16 |
| FR-M02 | Matching uses only that company's own active claims (not `rejected` or `superseded`) | Team | — | BR-11, BR-19 | UC-06 | P0 | T-04 |
| FR-M03 | Claim weights: company priorities > `company_provided` or `confirmed` > `stated` > `inferred`. Matches are recomputed synchronously after any profile change | Team | — | BR-09, BR-11 | UC-07 | P0 | T-19 |
| FR-M04 | Every match has an explanation of why it is relevant, citing at least one `supporting_claim_id` from the same company. Updates also say why the change could matter | Official / Team | p.3 item 6; p.2 item 1 | BR-23, BR-26 | UC-06 | P0 | T-16 |
| FR-M05 | Every match has a `next_step`, e.g. "Read the call text and eligibility requirements on the source page" or "Register on the event page". It is never a commitment by Blue Science Park | Official / Team | p.3 item 6; p.4 | BR-20, BR-23 | UC-06 | P0 | T-16 |
| FR-M06 | Funding matches are labelled "Potential match — eligibility not assessed", and their explanation lists key requirements and uncertainties (e.g. deadline not stated) | Official | p.3 item 4; p.4 step 3 | BR-20, BR-24 | UC-06 | P0 | T-17 |
| FR-M07 | Every match carries the standard disclaimer. Explanations contain none of the banned phrases in [security-privacy.md](security-privacy.md#honesty-rules) | Official / Team | p.3 Boundaries | BR-20 | UC-06 | P0 | T-16, T-17 |
| FR-M08 | Explanations never describe an `inferred` claim as a priority or as confirmed ("may be relevant because…", not "your priority is…") | Official / Team | p.2 | BR-08 | UC-06 | P0 | T-07 |
| FR-M09 | The same profile version and item set always produce the same ranking | Team | — | BR-11 | UC-06 | P0 | T-18 |
| FR-M10 | Users can save a match and give relevant / not relevant feedback; this is stored as company-private data | Official (journey example) | p.3 item 5; p.4 step 4 | BR-09 | UC-15 | P1 | — |
| FR-M11 | Feedback influences ranking | Official (area 5, not selected) | p.3 item 5 | BR-11 | UC-15 | P2 | — |
| FR-M12 | Suggest collaborations between members, explaining the basis without assuming either company has expressed an interest | Official (area 5, not selected) | p.3 item 5 | BR-01 | UC-18 | P2 | — |
| FR-M13 | Embedding-based or hybrid ranking | Team | — | BR-11 | UC-06 | P2 | — |

## FR-I: Interaction (Ask-Box) Requirements

Interface: a single ask-box with a response panel, in the context of the selected company (D-015). Design: [security-privacy.md §7](security-privacy.md#7-interaction-boundaries).

| ID | Requirement (acceptance criterion) | Origin | PDF | Meets | Use case | Priority | Test |
|---|---|---|---|---|---|---|---|
| FR-I01 | The user can submit a question through the ask-box and see the response in a panel | Official / Team | p.1 Scope (bullet 7); p.3 item 6 | BR-13 | UC-08 | P0 | T-20, T-32 |
| FR-I02 | Each request is classified as `in_scope`, `out_of_scope`, `unclear`, `boundary_override` or `needs_human`, and the response states which handling applied | Team | — | BR-13, BR-16 | UC-08–UC-12 | P0 | T-21 |
| FR-I03 | In-scope requests are answered only from the active company's profile and matches and from collected public items, with source links. Unsupported facts are not added | Official / Team | p.3 Boundaries; p.3 item 6 | BR-13, BR-23 | UC-08 | P0 | T-20 |
| FR-I04 | Out-of-scope requests get a brief remit statement plus a suggested relevant question or contact route | Official | p.3 Boundaries | BR-22 | UC-09 | P0 | T-21 |
| FR-I05 | Unclear requests get one focused clarifying question | Official | p.3 Boundaries | BR-22 | UC-10 | P0 | T-22 |
| FR-I06 | Override attempts (ignore your rules, reveal your instructions, act as another assistant) are declined; the remit is restated and the rules are unchanged | Official | p.1 Scope (bullet 7); p.3 Boundaries | BR-13, BR-18 | UC-11 | P0 | T-23 |
| FR-I07 | Follow-ups: the last 3 exchanges of the same company session are passed as context, and boundaries are re-applied on every turn, including role-adoption requests made later | Official / Team | p.3 Boundaries | BR-18 | UC-11 | P0 | T-24 |
| FR-I08 | Requests that need a human decision or commitment (eligibility decisions, Blue Science Park commitments, professional advice) are referred to Blue Science Park staff through the contact route in [sources.md](sources.md#reference-blue-science-park-contact-routes), labelled pending until that route is verified | Official / Team | p.3 Boundaries | BR-20, BR-21 | UC-12 | P0 | T-25 |
| FR-I09 | Responses distinguish information and suggested next steps from professional advice, eligibility decisions or commitments | Official | p.3 Boundaries | BR-20 | UC-08, UC-12 | P0 | T-25 |
| FR-I10 | Requests for another company's non-public profile data or user interactions are declined without revealing whether such data exists | Official | p.3 Boundaries | BR-19 | UC-13 | P0 | T-26 |
| FR-I11 | The assistant has no tools. Retrieved content is passed as delimited data only | Official / Team | p.3 Boundaries | BR-17 | UC-08 | P0 | T-27 |
| FR-I12 | Fail closed: if classification or generation fails or is invalid, return a safe remit-and-redirect response | Team | — | BR-13, BR-16 | UC-08–UC-12 | P0 | T-35 |
| FR-I13 | A company can view its own past questions; history is company-private | Team | — | BR-19 | UC-08 | P1 | — |
| FR-I14 | Full multi-turn chat, digests or alerts | Official (option) | p.3 item 6 | BR-23 | — | P2 | — |

## FR-U: User Interface Requirements

| ID | Requirement (acceptance criterion) | Origin | PDF | Meets | Use case | Priority | Test |
|---|---|---|---|---|---|---|---|
| FR-U01 | A company selector ("acting as", labelled as simulated sign-in) lists the demo members | Team | — | BR-14 | UC-06 | P0 | Demo |
| FR-U02 | The profile view groups claims by brief category. Each claim shows basis badge ("Stated on source", "AI-inferred — not a confirmed priority", "Provided by company"), review state, uncertainty flag and reason, evidence quote, source link and retrieval date | Official / Team | p.1 Scope; p.2 | BR-05–BR-08 | UC-02 | P0 | T-32 |
| FR-U03 | A "Missing information" panel lists `missing_fields` and shows completeness as "n of 6 categories documented". Inferred suggestions in a missing category are shown separately, labelled AI-inferred, and never counted as documented | Official / Team | p.2 | BR-07, BR-08 | UC-02 | P0 | T-32 |
| FR-U04 | Refinement actions: confirm, reject, edit, add, set or unset priority | Official / Team | p.1 Scope; p.4 step 2 | BR-09 | UC-03 | P0 | T-32 |
| FR-U05 | The findings dashboard shows, per match: title, type, relevant dates, source link, retrieval date, data-status label, explanation with cited claims, next step and disclaimer; plus funding fields (FR-O05), event fields (FR-O06) or update fields (FR-O07) | Official / Team | p.1 Scope; p.3 items 2, 4, 6; p.2 item 1 | BR-12, BR-23–BR-26 | UC-06 | P0 | T-32 |
| FR-U06 | Ask-box and response panel showing the handling category, answer, source links and any referral | Official / Team | p.1 Scope; p.3 | BR-13 | UC-08–UC-13 | P0 | T-32 |
| FR-U07 | A persistent banner states that this is a prototype using snapshot and/or simulated data; simulated features are labelled where they appear | Official | p.1 Scope (bullet 8) | BR-14 | All | P0 | T-31 |
| FR-U08 | Basic accessibility: semantic HTML, all actions keyboard-reachable, meaning never conveyed by colour alone, WCAG AA contrast | Official / Team | p.3 item 6 | BR-23 | All | P0 | T-33 |
| FR-U09 | Side-by-side comparison of three companies' top matches | Team | — | BR-11 | UC-14 | P1 | — |
| FR-U10 | Filter by type and date | Team | — | BR-23 | UC-06 | P1 | — |
| FR-U11 | Save and feedback buttons (FR-M10) | Official (journey example) | p.4 step 4 | BR-09 | UC-15 | P1 | — |
| FR-U12 | Staff view of shared interests across members | Official (user need, not in the prototype list) | p.2 Who you're building for | BR-01 | UC-18 | P2 | — |

## FR-S: Security and Privacy Requirements

Details: [security-privacy.md](security-privacy.md).

| ID | Requirement (acceptance criterion) | Origin | PDF | Meets | Use case | Priority | Test |
|---|---|---|---|---|---|---|---|
| FR-S01 | All external content (pages, items) enters every LLM call only inside delimited data blocks, with a system rule that it is data, not instructions | Official / Team | p.3 Boundaries | BR-17 | UC-01, UC-08 | P0 | T-27 |
| FR-S02 | No LLM call has tool, function or browsing access | Team | — | BR-17 | UC-01, UC-08 | P0 | T-27 |
| FR-S03 | LLM output is validated against Pydantic schemas. Invalid output is retried once, then the step fails safely | Team | — | BR-17 | UC-01, UC-08 | P0 | T-27 |
| FR-S04 | Fetch allowlist: outbound requests only to domains in the member list and the source register; `http`/`https` on ports 80/443; redirects only within the allowlist; 10 s and 2 MB limits | Team | — | BR-17 | UC-01, UC-04 | P0 | T-28 |
| FR-S05 | Only visible text is extracted from HTML (no `script`, `style`, comments or hidden elements) | Team | — | BR-17 | UC-01 | P0 | T-29 |
| FR-S06 | Company-private data (corrections, review states, priorities, questions and answers, saved items, feedback) is served only to requests carrying that company's session token; otherwise `403`. Tokens are simulated in the MVP and labelled | Official / Team | p.3 Boundaries | BR-19, BR-14 | UC-13 | P0 | T-30 |
| FR-S07 | The assistant's context contains only the active company's data and public items, never another company's private data | Official / Team | p.3 Boundaries | BR-19 | UC-13 | P0 | T-26 |
| FR-S08 | No schema fields for personal data (person names, emails, phone numbers) | Team | — | BR-19 | UC-02 | P0 | T-37 |
| FR-S09 | API keys come only from environment variables, and are never sent to the client, logged or committed | Team | — | — | — | P0 | T-37 |
| FR-S10 | Full SSRF protection for arbitrary URLs: DNS resolution check against private, loopback, link-local and reserved ranges; re-validation on every redirect | Team | — | BR-17 | UC-17 | P1 | — |
| FR-S11 | Scrub emails and phone numbers from stored evidence quotes | Team | — | BR-19 | UC-02 | P1 | — |
| FR-S12 | Automated key-leak scan of logs and responses | Team | — | — | — | P1 | — |
| FR-S13 | Audit log of profile changes | Team | — | BR-09 | UC-03 | P2 | — |

## NFR: Non-Functional Requirements

| ID | Requirement | Origin | PDF | Meets | Priority | Test |
|---|---|---|---|---|---|---|
| NFR-01 | **Traceability.** Every claim and item traces to a source URL and retrieval date | Official / Team | p.1 Scope; p.2 | BR-06, BR-12 | P0 | T-02, T-10 |
| NFR-02 | **Honesty.** UI, API, docs and pitch distinguish implemented, snapshot, seed and simulated | Official | p.1 Scope (bullet 8) | BR-14 | P0 | T-31 |
| NFR-03 | **Provider independence.** One LLM gateway with configurable provider and a mock provider for tests | Team | p.1 ("free to choose your tools") | — | P0 | T-27 |
| NFR-04 | **Reproducible setup.** The setup steps in [handover.md](handover.md) work on a fresh clone | Official / Team | p.2 What to deliver | DLV-04 | P0 | T-34 |
| NFR-05 | **Language.** Swedish and English source text are both processed | Team | — | BR-03, BR-10 | P0 | T-36 |
| NFR-06 | **Demo resilience.** The demo runs from stored snapshots and cached LLM output without network | Team | — | BR-14 | P1 | — |
| NFR-07 | **Cost control.** LLM responses cached by input hash | Team | — | — | P1 | — |
| NFR-08 | **Performance.** Profiling one member finishes in under 2 minutes | Team | — | — | P1 | — |

---

## Q: Open Questions

This is the only list of open questions. Resolved items are kept for traceability.

| ID | Question | Status | Affects |
|---|---|---|---|
| Q-01 | Do the relayed requirements match the brief? | **Resolved**: replaced by the brief's wording with page references (2026-11-12) | All BR |
| Q-02 | Which member companies, from which member list? May we name them in a public demo? | **Partly resolved**: real member companies, starting from a member list (p.1 Scope, p.2). **Open**: list source and naming | BR-02, BR-03, FR-P01 |
| Q-03 | Is there a formal judging rubric? | **Partly resolved**: p.4 "What a strong solution demonstrates" and DLV-03 (p.2). **Open**: formal rubric | Prioritisation |
| Q-04 | Are specific opportunity sources expected? | **Resolved**: not specified; at least two distinct public sources (p.1) | FR-O01 |
| Q-05 | May public company website text be sent to a commercial LLM API? | **Open** | FR-P04, NFR-03 |
| Q-06 | Is website-only research acceptable? | **Resolved**: other public sources "where available" (p.1 Scope) | BR-03, FR-P15 |
| Q-07 | What access-control level is expected? | **Partly resolved**: the rule is in p.3. **Open**: whether simulated sign-in is acceptable | BR-19, FR-S06 |
| Q-08 | Should the UI be in Swedish, English or both? | **Open** | FR-U*, NFR-05 |
| Q-09 | What does "collaboration" cover? | **Partly resolved**: connections between companies and potential partners (p.3). Area not selected for the MVP | FR-M12 |
| Q-10 | Must all areas be covered? | **Resolved**: choose one or two (p.1 Scope) | BR-15 |
| Q-11 | Which public Blue Science Park contact routes should referrals point to? | **Open** | FR-I04, FR-I08 |
| Q-12 | May the brief PDF be committed to the repository? | **Open** | Documentation |
| Q-13 | Does covering three brief areas (1, 2, 4) instead of "one or two" raise any concern with the organisers? | **Open** (team decision D-014) | BR-15 |
