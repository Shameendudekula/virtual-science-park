# Component Inventory

**Status:** Proposal. Components are named for React (PascalCase) and styled with the tokens in [design-system.md](design-system.md). Props reference fields from [../api-contract.md](../api-contract.md) and add nothing to the API. "P" is the build priority.

## P0 Core Set (approved)

The P0 frontend uses **22 reusable components** (DD-31). The detailed tables further down list every designed component. Rows whose priority is **P0** are either one of these 22 or a part or variant of one (named in the "Absorbs" column). Everything else is P1 or P2.

| # | Component | Absorbs (from the tables below) |
|---|---|---|
| 1 | `AppShell` | `SideNav`, `TopBar`, `CompanySwitcher`, `PrototypeBanner`, `Wordmark` |
| 2 | `Badge` | Variants: `BasisBadge`, `ReviewStateChip`, `DataStatusBadge`, `HandlingBadge`, `PotentialMatchLabel`, `PriorityMarker`, `SimulatedOverlay`, type chip |
| 3 | `Button` | `IconButton`, `LinkButton` |
| 4 | `FormField` | `TextInput`, `Textarea`, `Select`, `Toggle` |
| 5 | `Card` | `Section`, `Divider` |
| 6 | `Dialog` | `ClaimEditorDialog` and `RejectConfirmDialog` content |
| 7 | `Toast` | Refinement result ("n findings re-ranked") |
| 8 | `StateMessage` | `Skeleton`, `EmptyState`, `ErrorState`, `InlineAlert` |
| 9 | `CompanyTable` | `Table`, `CompanyRow` |
| 10 | `SourceMeta` | `SourceLink`, `RetrievedDate` |
| 11 | `ClaimRow` | `ClaimActions`, inline `EvidenceQuote`, `InferenceRationale`, `UncertaintyFlag` |
| 12 | `ClaimEditor` | Form content for add and edit (inside `Dialog`) |
| 13 | `MissingInfoPanel` | — |
| 14 | `CoverageBar` | `CoverageMeter` (6 segments), `ReviewProgress`, `ReviewQueue` rows |
| 15 | `TypeTabs` | — |
| 16 | `OpportunityCard` | `DateTile`, `FundingFacts` / `EventFacts` / `UpdateFacts`, `RelevanceDots`, rank "#n" + ↑/↓ marker, `NextStepLink`, `MatchList` |
| 17 | `WhyItMatches` | `WhyThisMatches`, `UncertaintyList` |
| 18 | `NextStepPanel` | Detail page action panel |
| 19 | `Disclaimer` | — |
| 20 | `AskBox` | `ExampleQuestions` (static) |
| 21 | `ResponseCard` | `AssistantResponsePanel`, `QuestionBubble`, `CitationList`, "Findings mentioned" (from citations), `ReferralCard`, `SuggestedQuestions`, `SessionThread` |
| 22 | `AssistantGuide` | `HandlingGuide`, `ScopeNote` |

Screens are compositions of these. For example, the dashboard summary card is `Card` + `CoverageBar` + `Badge` chips, and the detail header is `Card` + `DateTile`s + `Badge`.

## Shell and Navigation

| Component | Responsibility | Key props / data | Used on | P |
|---|---|---|---|---|
| `AppShell` | Sidebar + top bar + prototype banner + content slot | `companyId` | 03–08 | P0 |
| `SideNav` | Workspace navigation; future items shown disabled with a "Planned" chip in the clickable prototype only | `activeRoute` | 03–10 | P0 |
| `TopBar` | Company switcher, review status, assistant shortcut | `Company`, review counts | 03–08 | P0 |
| `CompanySwitcher` | "Acting as {name} · Simulated sign-in"; switching clears workspace state | `Company[]` | 03–08 | P0 |
| `PrototypeBanner` | Persistent honesty notice with link to `/about` (P1) | snapshot date | All | P0 |
| `Breadcrumbs` | Context on detail and review | route | 05, 07 | P1 |
| `Wordmark` | Logo + name + descriptor | `variant: light \| dark` | All | P0 |

## Honesty and Provenance

| Component | Responsibility | Key props / data | Used on | P |
|---|---|---|---|---|
| `BasisBadge` | Shows *Stated on source* / *AI-inferred* / *Provided by you* with icon, text and outline style | `ClaimBasis` | 03–05, 07, 08 | P0 |
| `ReviewStateChip` | Not reviewed / Confirmed / Rejected / Replaced | `ReviewState` | 04, 05 | P0 |
| `UncertaintyFlag` | Icon + reason text | `uncertain`, `uncertainty_reason` | 04, 05 | P0 |
| `PriorityMarker` | Flag icon; rendered only when `is_priority` is true (company-set) | `is_priority` | 04, 05, 07 | P0 |
| `DataStatusBadge` | Snapshot / Seed / Simulated / Live | `DataStatus`, `retrieved_at` | 03, 06, 07 | P0 |
| `SourceLink` | Domain in mono + external icon; new tab with `noopener noreferrer` | `source_url` | 04, 06–08 | P0 |
| `RetrievedDate` | "Retrieved 12 Nov 2026" in mono | `retrieved_at` | 04, 06, 07 | P0 |
| `EvidenceQuote` | Quote with teal rule + SourceLink + RetrievedDate (+ uncertainty) | `Evidence` | 04, 05 | P0 |
| `InferenceRationale` | "Why the AI inferred this", dashed amber rule; never styled as a quote | `inference_rationale` | 04, 05 | P0 |
| `EvidenceDrawer` | All evidence items for one claim | `ProfileClaim` | 04, 05 | P1 |
| `Disclaimer` | Standard disclaimer text from the API, not re-typed in the UI | `disclaimer` | 06–08 | P0 |
| `PotentialMatchLabel` | Funding label, never truncated | `match_label` | 03, 06, 07 | P0 |
| `SimulatedOverlay` | Diagonal-hatch marker for simulated features or data | `label` | Any | P0 |

## Profile

| Component | Responsibility | Key props / data | Used on | P |
|---|---|---|---|---|
| `ProfileHeader` | Name, website, summary (labelled "AI-generated summary"), version, last researched date, profile data-status badge | `Company`, `CompanyProfile` | 04 | P0 |
| `CompanySummaryHero` | Dashboard focal point: identity, AI summary, 2×2 facets with basis chips, coverage footer; hosts `ReviewQueue` | `Company`, `CompanyProfile` | 03 | P0 |
| `ReviewQueue` | Stacked review bar + actionable rows (inferred to review, uncertain to check, missing to add) | claims, `missing_fields` | 03 | P0 |
| `SelectedClaimPanel` | Supporting panel: the selected claim, uncertainty callout, all evidence, actions | `ProfileClaim` | 04, 05 | P1 |
| `ReviewStatusPanel` | Counts by review state | claims | 04, 05 | P1 |
| `CoverageMeter` | 6 segments, one per documentable category (`relevant_topic` excluded, D-020); filled if documented; derived from `missing_fields` | `missing_fields` | 03, 04 | P0 |
| `ReviewProgress` | "8 of 12 claims reviewed" | claims | 03, 04, 05 | P0 |
| `ProfileSection` | One brief category with its claims | `ClaimCategory`, claims | 04, 05 | P0 |
| `ClaimRow` | Value + badges + evidence preview + actions (review mode) | `ProfileClaim` | 04, 05 | P0 |
| `ClaimActions` | Confirm · Edit · Reject · Set priority | `PATCH` actions | 05 | P0 |
| `ClaimEditorDialog` | Edit or add a claim; category select; priority toggle | `POST` / `PATCH` | 05 | P0 |
| `RejectConfirmDialog` | Confirms rejection; explains that it will no longer be used for matching | — | 05 | P0 |
| `MissingInfoPanel` | Lists missing categories with "Add information" | `missing_fields` | 04, 05 | P0 |
| `ImpactSummary` | Rank changes before/after refinement (computed client-side) | two `Match[]` snapshots | 05 | P1 |
| `ProfileVersionHistory` | Version list | — (P1 endpoint not defined) | 04 | P1 |

## Findings

| Component | Responsibility | Key props / data | Used on | P |
|---|---|---|---|---|
| `TypeTabs` | Funding · Events · Updates with counts | `type` query | 06 | P0 |
| `MatchList` | Ranked OpportunityCards; keyboard navigable | `Match[]` | 03, 06 | P0 |
| `OpportunityCard` | Date tile · meta row · title · type facts · "Why it matches" with claim chips · rank + relative relevance · Next step (replaces `MatchRow`) | `Match` | 03, 06 | P0 |
| `FeaturedMatchCard` | Larger #1 card on the dashboard with the full potential-match label and next step | `Match` | 03 | P1 |
| `DateTile` | DEADLINE / EVENT / PUBLISHED label, date, relative time; urgent and "Not stated in source" variants | dates, `date_unknown` | 03, 06, 07, 08 | P0 |
| `KeyDateTiles` | Four-tile header row on the detail page (type-specific) | `Match` | 07 | P1 |
| `EligibilityBlock` | One quoted block of `eligibility_summary`, "as stated by the source" + "not an assessment" note; never split into a list | `eligibility_summary` | 07 | P0 |
| `SourceRecord` | Expandable record of what was collected: source, URL, retrieved time, data status, language, original text | `Opportunity` | 07 | P1 |
| `NextStepPanel` | Next-step text + Open source / Ask assistant / Save (P1) + staff contact block | `next_step`, `source_url` | 07 | P0 |
| `RelevanceDots` | 5 dots from score quintile, with an `aria-label` like "Relevance 4 of 5 (relative)" | `score` | 03, 06, 07 | P0 |
| `FundingFacts` | Funder, purpose, deadline, eligibility summary ("Not stated in source" when null) | funding fields | 06, 07 | P0 |
| `EventFacts` | Format, audience, start/end, location, organiser | event fields | 06, 07 | P0 |
| `UpdateFacts` | Published date, what changed | update fields | 06, 07 | P0 |
| `WhyThisMatches` | Explanation + cited claims as BasisBadge chips linking to the profile | `explanation`, `supporting_claim_ids` | 07 | P0 |
| `UncertaintyList` | Bullet list of `uncertainties` | `uncertainties` | 07 | P0 |
| `NextStepLink` | Compact "Next step →" action on cards (the full version is `NextStepPanel`) | `next_step` | 03, 06 | P0 |
| `KeyDates` | Deadline / start / published, with relative time ("in 23 days") | dates, `date_unknown`, `expired` | 03, 06, 07 | P0 |
| `FilterPanel` | Dates, format, source, "based on", plus the "How ranking works" box; collapses on mobile (replaces `FindingFilters`) | — | 06 | P1 (box P0) |
| `SaveButton`, `FeedbackButtons` | Save; relevant / not relevant | P1 endpoints | 06, 07 | P1 |

## Assistant

| Component | Responsibility | Key props / data | Used on | P |
|---|---|---|---|---|
| `AskBox` | Textarea, counter (500), submit; disabled while waiting | `question` | 08 | P0 |
| `ExampleQuestions` | 4 team-written in-scope examples (static, labelled "Examples") | — | 08 | P0 |
| `AssistantResponsePanel` | Response card: header (handling badge + context used), answer, "Findings mentioned" and "Sources" zones, referral, suggestions, next-step strip, disclaimer | `AssistantResponse` | 08 | P0 |
| `QuestionBubble` | The user's question, right-aligned (labelled "YOU" or "YOU · FOLLOW-UP") | local state | 08 | P0 |
| `ContextPanel` | Static description of what the assistant uses (FR-I03); no counts or versions; privacy sentence only after T-26 passes (P0 version is part of `AssistantGuide`) | `CompanyProfile`, matches meta | 08 | P1 |
| `HandlingGuide` | The 5 handling badges with one-line explanations | — | 08 | P0 |
| `ContextualSuggestions` | 3 client-side question templates filled from the company's own top findings and claims | `Match[]`, claims | 08 | P1 |
| `HandlingBadge` | Answered / Outside scope / Needs clarification / Request declined / Referred to staff | `handling` | 08 | P0 |
| `CitationList` | Numbered source links | `citations` | 08 | P0 |
| `ReferralCard` | "Blue Science Park staff" + route + route status (pending → simulated label) | `referral` | 08 | P0 |
| `SuggestedQuestions` | Clickable follow-ups returned by the API | `suggested_questions` | 08 | P0 |
| `SessionThread` | Oldest → newest exchanges in the current page session; the server separately uses the last 3 as context | local state | 08 | P0 |
| `ScopeNote` | Static note: what the assistant can help with (brief p.3 list) | — | 08 | P0 |
| `AskAboutThis` | Deep link from a finding to the assistant, prefilled | `Match` | 07 | P1 |

## Generic

| Component | Responsibility | P |
|---|---|---|
| `Button`, `IconButton`, `LinkButton` | Variants per design system | P0 |
| `TextInput`, `Textarea`, `Select`, `Toggle` | Form controls with labels and errors | P0 |
| `Card`, `Section`, `Divider` | Layout surfaces | P0 |
| `Table` | Company list | P0 |
| `Dialog`, `Drawer` | Focus-trapped overlays | P0 |
| `Toast`, `InlineAlert` | Feedback | P0 |
| `Skeleton`, `EmptyState`, `ErrorState` | System states | P0 |
| `Tooltip` | Short definitions (e.g. "What does *stated* mean?") | P1 |
| `CompanyCard` / `CompanyRow` | Company selection entries | P0 |
| `SearchInput` | Company search (client-side over `GET /companies`) | P1 |

## Usage Examples

```tsx
<ClaimRow claim={claim} mode="review">
  <BasisBadge basis={claim.basis} />
  {claim.is_priority && <PriorityMarker />}
  {claim.uncertain && <UncertaintyFlag reason={claim.uncertainty_reason} />}
</ClaimRow>

<OpportunityCard match={m} onOpen={() => navigate(`/c/${companyId}/findings/${m.id}`)} />

<AssistantResponsePanel response={res} />   // renders HandlingBadge first, always
```

**Rule:** components render labels from API values. They never infer basis, handling or data status on the client ([../architecture.md](../architecture.md#frontend-and-backend-responsibilities)).
