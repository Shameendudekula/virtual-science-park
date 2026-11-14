# Prototype Plan

**Status:** Approved P0 plan for Phase 2 (D-019, 2026-11-12). Nothing is built yet. Requirement priorities come from [../requirements.md](../requirements.md). UI-to-API rules: [api-ui-consistency.md](api-ui-consistency.md).

## Principle

**One coherent end-to-end demo before any extra screen.** The build follows the brief's required flow (p.1): member discovery → profile → refinement → personalised findings → boundaries. P0 is desktop-first (≥ 1280 px, DD-30).

## Screen Priorities

| Priority | Screens and elements |
|---|---|
| **P0** | **02** Company table. **03** Dashboard: summary card + review queue + top 5 OpportunityCards. **04/05** Profile with always-visible refinement actions and inline evidence. **06** Findings: type tabs + sort + OpportunityCards. **07** Finding detail: date tiles, potential-match band, one eligibility block, why it matches, uncertainties, next-step panel. **08** Assistant: ask-box, static examples, response cards, guide panel. Prototype banner, simulated sign-in label, data-status labels, refinement toast + ↑/↓ markers |
| **P1** | 01 Landing · 12 Sources & transparency · filter panel · review filter chips · selected-claim panel · impact drawer · featured card + three dashboard columns · source record · contextual assistant suggestions · save/feedback · comparison view (FR-U09) · profile version history · responsive tablet and mobile layouts |
| **P2** | 09 Connections · 10 Settings · 11 Staff view · digests and alerts |

## Data Strategy for the Frontend

| Phase | Data | Label shown |
|---|---|---|
| Before the backend exists | Mock JSON in `data/mock/`, matching [../api-contract.md](../api-contract.md) exactly. Fictional companies A–C, findings from "Example source", `.test` domains, "Example venue" | **Fictional sample** / **Simulated** on every record (`data_status = simulated`) |
| Integration | Real API: profiles generated from real member sites (after Q-02), snapshots from tested sources | **Snapshot · retrieved {date}**; the simulated sign-in label stays |

**Rule:** mock data never uses real member names, real funders, real call titles, real places or real staff contacts.

## Confirmed P0 Implementation Sequence

| Step | Work | Components (core set) | Depends on | Done when |
|---|---|---|---|---|
| 1 | Vite + React + TypeScript + Tailwind scaffold; theme from tokens; **self-hosted fonts** (DD-27); bundled Lucide icons | — | Phase 2 go-ahead | App builds; no external font or icon requests |
| 2 | App shell with simulated sign-in, an in-memory token store, and **state reset on company switch** (DD-29) | 1 `AppShell` | Step 1 | Switching company clears profile, matches, assistant thread and toasts |
| 3 | Shared kit | 2 `Badge`, 3 `Button`, 4 `FormField`, 5 `Card`, 6 `Dialog`, 7 `Toast`, 8 `StateMessage`, 10 `SourceMeta`, 19 `Disclaimer` | Step 1 | T-31 labels render |
| 4 | Mock API layer typed from the contract; mock JSON for 3 fictional companies | — | API contract agreed | Types compile against all schemas |
| 5 | **02 Company table** | 9 `CompanyTable` | Steps 2–4 | Select → workspace |
| 6 | **04/05 Profile + refinement** (inline evidence; confirm, reject, edit, add, priority; completeness "n of 6") | 11 `ClaimRow`, 12 `ClaimEditor`, 13 `MissingInfoPanel`, 14 `CoverageBar` | Step 3 | T-32 profile parts; FR-P09 display correct |
| 7 | **06 Findings + 07 Detail** (tabs, sort, rank "#n", type facts, eligibility block, next step) | 15 `TypeTabs`, 16 `OpportunityCard`, 17 `WhyItMatches`, 18 `NextStepPanel` | Step 3 | Every finding shows source, retrieved date, data status and disclaimer |
| 8 | Refinement impact: toast + ↑/↓ markers (client-side diff) | 7 `Toast`, 16 | Steps 6–7 | A priority change visibly re-ranks findings |
| 9 | **08 Assistant** with a mocked `AssistantResponse` for all five handling values; findings matched from citations only | 20 `AskBox`, 21 `ResponseCard`, 22 `AssistantGuide` | Step 3 | All handling badges render; no unsupported fields used |
| 10 | **03 Dashboard** (composes existing components) | 5, 14, 16 | Steps 6–7 | Summary card, review queue, top 5 |
| 11 | Switch from mocks to the real API; loading, empty and error states | 8 | Backend P0 endpoints | Demo runs on real data |
| 12 | Accessibility pass (axe, keyboard) and copy review against the honesty rules | — | All | T-33; honesty checklist |

**Day-2 checkpoint** (matches the D-014 cut rule): if steps 1–11 are not working end to end, stop all P1 work and drop *Updates* from the UI before anything else.

## Frontend Tests Mapped to Requirements

| Test | Components |
|---|---|
| T-32 | `Badge` (basis, review, uncertainty, priority), `MissingInfoPanel` (n of 6, inferred suggestions separate), `ClaimRow` actions, `OpportunityCard` + type facts, `NextStepPanel`, `Disclaimer`, `ResponseCard` for each handling value |
| T-31 | `AppShell` banner, `Badge` data status, simulated sign-in label |
| T-33 | Axe on profile, findings and assistant; keyboard path through claim actions and the ask-box |

## Demo Readiness Checklist (UI)

- [ ] Three companies selectable; their top findings differ visibly
- [ ] Each profile shows its stated, inferred and missing items as the data has them (never faked)
- [ ] A refinement produces a toast and visible ↑/↓ rank changes
- [ ] A funding detail shows the potential-match band, the eligibility block as stated, the deadline, the next step and the source
- [ ] The assistant shows Answered, Outside scope, Request declined (including a follow-up), Needs clarification and Referred to staff
- [ ] Banner, simulated sign-in and data-status labels are visible in every screenshot used in the pitch
- [ ] No isolation claims on screen unless T-26 and T-30 pass
- [ ] Product name and Blue Science Park mentions follow the DD-03 fallback until organisers approve
