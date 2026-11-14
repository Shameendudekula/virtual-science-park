# Design Decisions

**Status:** Reviewed and approved by the team lead on 2026-11-12 as the design baseline (project decision [D-019](../decisions.md)). The project log [../decisions.md](../decisions.md) remains the authoritative record.

| Status value | Meaning |
|---|---|
| **Accepted** | Approved as written |
| **Accepted (amended)** | Approved with the change stated in the entry |
| **Pending organiser** | Needs Blue Science Park or organiser permission; build with a fallback until confirmed |

## Decisions

| ID | Decision | Status | Rationale | Affects |
|---|---|---|---|---|
| DD-01 | **Concept: "Innovation Intelligence Workspace".** One workspace per company: Profile → Findings → Assistant | Accepted | Mirrors the brief's flow (p.1) and example journey (p.4) | IA, all screens |
| DD-02 | **App shell with a navy sidebar and a light content area**, desktop-first. *Widths superseded by DD-20* | Accepted | Enterprise credibility; readable dense data | All |
| DD-03 | **Name "Virtual Science Park — AI-Powered Innovation Intelligence", with our own "lens and node" mark; no Blue Science Park logo, colours or logotype** | Accepted (visual identity) · **Pending organiser** (use of the name, and naming Blue Science Park in the UI) | "Virtual Science Park" is Blue Science Park's concept name in the brief; we must not imply endorsement. **Fallback until approved:** keep the name as a working title, and the landing overline without "Blue Science Park" | Shell, landing |
| DD-04 | **Palette:** ink (navy) + paper (warm off-white) + one teal accent; semantic colours; all text pairs ≥ 4.5:1 | Accepted | Calm, credible, accessible | All |
| DD-05 | **Type:** Manrope, Inter, IBM Plex Mono; Lucide icons | Accepted (amended by DD-27: self-hosted) | Open licences; mono makes provenance scannable | All |
| DD-06 | **Basis shown by icon + text + colour + outline style.** "Stated on source", never "Verified" | Accepted (amended) | **Amendment:** a priority marker never replaces the basis label; a priority claim shows both (e.g. "Provided by you" + flag) | 03–08 |
| DD-07 | **At most 6 cards above the fold; lists as rows or single-column cards** | Accepted | Avoids dashboard clutter | 03, 06 |
| DD-08 | **No percentages or invented metrics.** Rank + relative relevance dots; completeness as **"n of 6 categories documented"** | Accepted (amended) | **Amendment:** `relevant_topic` excluded (D-020) | 03, 04, 06, 07 |
| DD-09 | **Refinement is part of the profile screen** | Accepted (amended) | **Amendment:** no View/Review toggle; actions always visible. Review filter chips are P1 | 04, 05 |
| DD-10 | **Monitoring interests = company-set priorities in the profile** | Accepted | One source of truth (FR-P10) | 05, 10 |
| DD-11 | **Refinement impact computed client-side** from two match lists | Accepted (amended) | **Amendment:** P0 shows a toast plus ↑/↓ rank markers; the impact drawer is P1 | 05, 06 |
| DD-12 | **Finding detail reads from the cached match list**; API gaps recorded, not added | Accepted | Respect the agreed API contract | 02, 07 |
| DD-13 | **Assistant on a dedicated page**; every response starts with its handling badge | Accepted | Boundary behaviour is visible and demonstrable | 03, 08 |
| DD-14 | **Example questions are static and team-written**; follow-up suggestions only from the API | Accepted (prevails over DD-24 in P0) | Avoids presenting invented content as AI output | 08 |
| DD-15 | **Persistent prototype banner, simulated sign-in label, data-status badge on every finding and profile** | Accepted | BR-14 | All |
| DD-16 | **Landing page is P1**; P0 starts at company selection | Accepted | The brief requires the flow, not a marketing page | 01, 02 |
| DD-17 | **Connections, Settings and Staff view are P2 design-only screens** | Accepted | **Clarification:** hidden in the demo build; shown as "Planned" only in the mockup | 09–11 |
| DD-18 | **Mock data is fictional or simulated, with neutral names and places** ("Example source", "Example venue", `.test` domains) | Accepted | Never mistakable for real companies, calls or places | Mockups, mock JSON |
| DD-19 | **Minimal motion** | Accepted | The rank-change pulse is optional | All |
| DD-20 | **Layout system v2:** sidebar 240 px; workspace up to 1440 px; 360 px supporting panel; thresholds 1360/1180/900 | Accepted (amended by DD-30) | Uses desktop space; consistent across screens | All |
| DD-21 | **Dashboard focal point = company summary card + review queue** | Accepted (amended) | **Amendment:** the featured #1 card and the three bottom columns are P1; the P0 dashboard is the summary card, review queue and top 5 OpportunityCards | 03 |
| DD-22 | **OpportunityCard anatomy:** date tile / content / rank + relative relevance + next step | Accepted (amended) | **Amendment:** rank shown as "#n" only | 03, 06 |
| DD-23 | **Profile = claims (main) + supporting panel** | Accepted (amended) | **Amendment:** P0 evidence opens inline under each claim; the supporting panel holds completeness, review counts, missing information and sources. The selected-claim panel is P1 | 04, 05 |
| DD-24 | **Assistant = conversation card + side panel; response cards in zones** | Accepted (amended) | **Amendment:** keep `AssistantResponse` unchanged; no per-response "context used" line and no next-step strip; "Findings mentioned" only from citations matching already-loaded findings; contextual suggestion templates are P1 ([api-ui-consistency.md](api-ui-consistency.md#assistant-s08-with-assistantresponse-unchanged)) | 08 |
| DD-25 | **Finding detail:** header with date tiles and a potential-match band; next-step panel | Accepted (amended) | **Amendment:** eligibility shown as **one quoted block** of `eligibility_summary`; rank "#n"; the source record is P1 | 07 |
| DD-26 | **Mockup controls visually separate from the product** | Accepted | Reviewers must not mistake mockup controls for features | Mockup |
| DD-27 | **Fonts self-hosted** in the application; Google Fonts never loaded at runtime | Accepted | Privacy (no third-party IP disclosure) and offline demo resilience. The mockup is exempt as a design reference | All |
| DD-28 | **API/UI consistency rule:** every P0 UI element maps to an existing API field or is derived from loaded data; otherwise it is removed or P1 | Accepted | Keeps the frontend honest to the contract ([api-ui-consistency.md](api-ui-consistency.md)) | All |
| DD-29 | **Simulated sign-in stays labelled. Switching company clears all company-specific UI and assistant state.** The token is held in memory only. No isolation claims until T-26 and T-30 pass | Accepted | FR-S06, FR-S07; honesty | Shell, 08 |
| DD-30 | **Desktop-first P0 (≥ 1280 px); mobile and tablet responsiveness P1** | Accepted | Three-day timeline; the demo is shown on a laptop or projector | All |
| DD-31 | **P0 component set of about 22 reusable components** ([component-inventory.md](component-inventory.md#p0-core-set-approved)) | Accepted | Fits the build time | All |

## Still Pending

| # | Item | Owner | Fallback until resolved |
|---|---|---|---|
| 1 | Use of the product name "Virtual Science Park" and of "Blue Science Park" in UI text (DD-03) | Organisers | Working title; functional references only (disclaimer, referral); no Blue Science Park overline |
| 2 | Staff contact route for referrals (Q-11) | Organisers | "Contact route pending verification" + Simulated label |
| 3 | Real demo companies (Q-02) | Organisers / team | Fictional companies, labelled, in all mockups and mock data |
| 4 | UI language (Q-08) | Organisers / team | English UI; source text shown in its original language |
| 5 | Final logo artwork | Team | Primitive SVG mark from [design-system.md](design-system.md#1-identity) |
