# Screen Specifications

**Status:** Proposal, Figma-ready. Tokens and components: [design-system.md](design-system.md), [component-inventory.md](component-inventory.md). Routes and endpoints: [information-architecture.md](information-architecture.md).

**Sample content policy:** all example text below uses **fictional** companies (A: maritime IoT sensors, B: cybersecurity software, C: circular food-tech; see [../research/challenge-analysis.md](../research/challenge-analysis.md)) and **simulated** findings from "Example source". In any mockup they must carry a visible *Fictional sample* or *Simulated* badge. Real member data replaces them only once Q-02 is resolved and the profiles have been generated from public sources.

## Overview

| # | Screen | Frame name | Priority | Main requirements |
|---|---|---|---|---|
| 01 | Welcome / landing | `01 Welcome — Desktop 1440` | **P1** (P0: short intro block on 02) | BR-01, DLV-01 |
| 02 | Company selection | `02 Companies — Desktop 1440` | **P0** | BR-02, FR-U01 |
| 03 | Dashboard | `03 Dashboard — Desktop 1440` | **P0** | BR-01, BR-11, BR-12 |
| 04 | Intelligence profile | `04 Profile — Desktop 1440` | **P0** | BR-04–BR-08, FR-U02, FR-U03 |
| 05 | Review & refine (mode of 04) | `05 Profile Review — Desktop 1440` | **P0** | BR-09, FR-P12, FR-M03 |
| 06 | Findings discovery | `06 Findings — Desktop 1440` | **P0** (filters P1) | BR-10–BR-12, BR-24–BR-26 |
| 07 | Finding detail | `07 Finding Detail — Desktop 1440` | **P0** | BR-20, BR-23–BR-26, FR-M04–M06 |
| 08 | Innovation assistant | `08 Assistant — Desktop 1440` | **P0** | BR-13, BR-16–BR-22 |
| 09 | Connections | `09 Connections — Desktop 1440` | **P2** | FR-M12 |
| 10 | Settings & preferences | `10 Settings — Desktop 1440` | **P2** (feedback parts P1) | FR-M10, FR-I13 |
| 11 | Staff view | `11 Staff — Desktop 1440` | **P2** | FR-U12 |
| 12 | Sources & transparency | `12 About — Desktop 1440` | **P1** | BR-14, DLV-02 |

**Approved P0 scope (D-019, DD-21–DD-25, DD-30):**
- **P0 screens:** 02, 03 (reduced), 04 + 05 (one page), 06 (tabs + sort), 07, 08.
- **Desktop-first:** ≥ 1280 px. The ≤ 1180 and ≤ 900 behaviour below is P1.
- **API use:** every element follows [api-ui-consistency.md](api-ui-consistency.md).
- **Marking:** items marked *(P1)* below are designed but not built in P0.

**Common to all workspace screens (03–10), layout system v2 ([design-system.md §4](design-system.md#4-spacing-radius-elevation-layout)):**
- **Frame:** 1440 × 1024 (scrollable height); also check at 1680, 1024 and 390.
- **AppShell:** sidebar **240 px**; a 36 px PrototypeBanner and a 64 px sticky TopBar over the main area.
- **Main workspace:** flexible width, **content max 1440 px**, centred; horizontal padding 32 px (24 px ≤ 1180 px, 16 px ≤ 900 px).
- **Two-column pattern:** `minmax(0,1fr)` main + **360 px supporting panel** (330 px ≤ 1360 px; stacked ≤ 1180 px). Findings uses a **260 px filter panel on the left** instead.
- **Gap:** 24 px between all major blocks. No fixed narrow content columns: text measures are limited by `max-width` in characters, not by column width.
- **Page header:** overline + `h1` + one-line meta on the left; actions and badges on the right.

---

## S01. Welcome / Landing (P1)

**Purpose:** explain the value in 10 seconds and lead to company selection.

**Layout** (no sidebar; a slim top bar with the wordmark and an "About this prototype" link):
1. **Hero** (8 cols text + 4 cols visual):
   - overline "BLUE SCIENCE PARK · VIRTUAL SCIENCE PARK" (with permission, DD-03);
   - `display` headline: "Know what's relevant to your business — and why.";
   - `body-lg` text: "We read member companies' public websites, build an evidence-backed profile you can correct, and match it with funding calls, events and updates from public sources.";
   - Primary button "Choose a company"; secondary "How it works".
   - Visual: a static, *real-component* preview of one claim row and one finding row (fictional, labelled). No illustration and no fake stats.
2. **How it works:** 4 numbered steps in a row: Public sources → Evidence-backed profile → You refine → Explained findings. Each has a 20 px icon and two lines of text.
3. **Trust strip:** three short statements: "Every claim shows its source and date" · "AI inferences are labelled, never presented as facts" · "Suggestions, not eligibility decisions". These describe design rules, not metrics.
4. **Footer:** prototype notice, team, event name.

**States:** static page; no loading states.
**Responsive:** the hero stacks below `lg`; steps become a 2×2 grid, then a column.

## S02. Company Selection (P0)

**Purpose:** start from the member list; choose a workspace. **Data:** `GET /companies`.

**Layout:**
1. **Header:** `h1` "Choose a member company"; description "Profiles are generated from public sources and can be refined by the company."
   - P0 intro block (replaces landing): 3 short lines on what the service does, plus a link "What's real in this prototype?"
2. **Toolbar:** SearchInput (filters name and website on the client); count "3 companies". Sector filters are P1, because the API returns no sector field on `Company` (**Gap**, DD-12).
3. **Company list:** a Table (preferred for credibility) with columns:
   - Company (name + website domain in mono);
   - Source of member entry (`member_list_source`);
   - DataStatusBadge;
   - Action "Open workspace →".
   Optional P1: a profile summary line from `GET /profile`, which requires one profile call per company.
4. **Simulated sign-in note:** "Selecting a company simulates signing in as that company. Real authentication is not part of this prototype."

**Interaction:** clicking a row → `/c/:id`. Keyboard: arrow keys move between rows; Enter opens.
**States:**
- Loading: 3 skeleton rows.
- Empty: "No member companies configured. The member list is set up in the demo build" (with a developer hint).
- Error: inline alert + Retry.
**Responsive:** below `md`, the table becomes stacked rows.

## S03. Dashboard (P0)

**Purpose:** one glance answers: what do we know about this company, how sure are we, and what should it look at now?
**Data:** `GET /companies/{id}`, `GET …/profile`, `GET …/matches?limit=20` (grouped by type on the client).

**Layout (v2, Phase 1.5):**
1. **Page header:**
   - overline "WORKSPACE"; `h1` "Overview";
   - meta: "Profile researched 12 Nov 2026 · Findings from snapshots collected 12 Nov 2026";
   - actions: secondary "View all findings", primary "Continue review".
2. **Focal point: CompanySummaryHero** (full width; one card split into a flexible main area and a 380 px side panel, 340 px below 1360 px; it stacks below 1180 px):
   - **Main area:**
     - identity row (avatar, name, domain, profile version);
     - *AI-generated summary* (`body-lg`);
     - a 2 × 2 facet grid, "What it offers", "Technologies", "Markets & customers" and "Your priorities", each showing 1–2 claim chips with basis badges;
     - **coverage footer:** a 6-segment bar, "4 of 6 categories documented" (`relevant_topic` excluded, D-020), the missing categories named, and a "Fill 2 gaps" action.
   - **Side panel: ReviewQueue**:
     - "4 / 12 reviewed", with a stacked bar (confirmed · provided by you · not reviewed) and a legend;
     - three actionable rows: *n AI-inferred claims* → Review; *n uncertain* → Check; *n missing categories* → Add;
     - note "Your confirmations and priorities count most in ranking".
     - This replaces the earlier decorative "3 steps" strip.
3. **Recommended for you:**
   - section header "Top matches for your profile" + "Ranked against profile v3 · snapshot date" + a Simulated badge;
   - *(P1)* **FeaturedMatchCard** (#1, about 60 % width, teal outline): type chip, full potential-match label, title (22 px), date line with days left, a "Why this matches you" panel with cited claim chips, next-step line and the primary "Open finding";
   - beside it, **two compact OpportunityCards** (#2, #3).
4. *(P1, DD-21)* **Three equal columns:**
   - *Upcoming events*, *Funding deadlines* and *Recent updates*;
   - each has 2–3 rows: a date column (mono) plus title and one meta line ("Potential match", format, "what changed").

**States:**
- Loading: hero skeleton + card skeletons.
- No findings: "No current findings match this profile in the latest snapshot ({date}). Adding priorities in your profile can widen matching."
- Per-card errors: the rest of the page still renders.
- Success: after a refinement, a toast with an impact link.

**P0 dashboard (DD-21):** summary card + review queue + the top 5 as standard OpportunityCards, each with its own data-status label. **Responsive (P1, DD-30):** ≤ 1180 px: the hero and featured row stack. ≤ 900 px: the sidebar becomes a top tab bar, and the three columns become one.

## S04. Company Intelligence Profile (P0)

**Purpose:** show exactly what is known, how it is known, and what is missing. **Data:** `GET …/profile`.

**Layout (v2):** a header row, then a **two-column split**: claims on a flexible main side, and a 360 px supporting panel (330 px below 1360 px; it stacks below 1180 px).
1. **Header:**
   - overline, `h1` company, "Version · Researched · domain";
   - right side: the profile **data-status badge** (from `CompanyProfile.data_status`) and, in mockups, the Fictional sample badge. There is no View/Review toggle; refinement actions are always visible (DD-09).
2. **Legend bar:** the three basis badges, each with a one-line definition ("The source said this when retrieved, not proof it is still true").
3. **Main side: one card per brief category, in brief order** (offering · technologies & expertise · application areas · markets & customers · geographic focus · stated projects & collaborations · relevant topics):
   - card header: category name + count, or a note ("Inferred topics are suggestions, not your priorities");
   - **ClaimRow** in two columns: the left holds the value (15 px semibold), a badge row (basis, review state, priority, uncertainty) and a compact source line (domain + retrieved date); the right holds the **action group** (see S05);
   - inferred claims show the InferenceRationale (dashed amber rule) instead of a source line;
   - missing categories show a dashed "Not stated on any public source we reviewed" row with "+ Add information";
   - the last card's footer: "Hidden: n rejected · n replaced · Show".
4. **Supporting panel** (sticky at 88 px from the top):
   - *(P1, DD-23)* **SelectedClaimPanel:** claim, badges, uncertainty explanation (rust callout), **all evidence** (quote, link, retrieved date, source type, page date), and actions (Confirm · Correct · Reject);
   - **ReviewStatusPanel:** counts for confirmed / provided / not reviewed / uncertain / rejected / replaced;
   - **What we don't know yet:** missing categories + "Add information";
   - **Sources used:** domains, page counts, retrieved date.

**P0 (DD-23):** each ClaimRow expands **inline** to show all its evidence; the supporting panel holds completeness, review status, missing information and sources. *(P1)* Selecting a claim row (click or Enter) highlights it (teal inset rule and tint) and loads its evidence into the panel. This replaces the evidence drawer on desktop; the drawer remains for screens ≤ 1180 px.

**States:** loading (section skeletons); no profile ("This company has not been profiled yet. Profiles are generated by the demo build"); error.

## S05. Profile Review and Refinement (P0, part of S04)

**Purpose:** a human-controlled correction loop with visible impact.
**Data:** `PATCH …/claims/{id}`, `POST …/claims`, then `GET …/matches`.

**Layout:** S04 itself (no separate mode, DD-09), plus:
1. **Notice bar** (teal-50, under the header): "Changes save immediately and are visible only to your company". *(P1)* Filter chips: All · Not reviewed · AI-inferred · Uncertain.
2. **Action group per ClaimRow** (always visible in review mode, 30 px outlined buttons with icon + text):

   | Claim state | Actions |
   |---|---|
   | Not reviewed (stated or inferred) | **Confirm** (teal) · **Edit** · **Reject** (rust) |
   | Confirmed | Shows "✓ Confirmed by you"; Edit · Set priority |
   | Company-provided | Edit · Set priority, or **Priority** (indigo, pressed) |

   Rejecting opens a confirmation dialog. Editing opens ClaimEditorDialog ("Your version replaces the AI version; the original stays under *Hidden claims*").
3. **Add information:** from missing rows and the panel → ClaimEditorDialog with the category preselected and a "Mark as priority" toggle.
4. **P0 (DD-11):** after a change, a toast "n findings re-ranked · View findings", and ↑/↓ markers next to the ranks in Findings (computed client-side). *(P1)* **ImpactSummary drawer** (after the first change; then via a "View impact" chip): "↑3 moved up · 1 new in your top 10 · 1 dropped out", plus the rank changes and the claim that caused each one.

**Interaction:** optimistic UI with rollback ("Couldn't save — your change was undone"). The badge change animates (`motion-base`); ranks pulse once (`motion-emph`).
**Copy rule:** inferred items say "may be relevant", never "your priority".

## S06. Findings Discovery (P0; filter panel P1)

**Purpose:** browse personalised findings by type. **Data:** `GET …/matches?type=`.

**Layout (v2):**
1. **Header:** `h1` "Findings for {company}"; meta "From 2 public sources · Snapshot collected {date} · Ranked against profile v{n}"; Simulated badge.
2. **TypeTabs (P0):** All · Funding · Events · Updates, with counts.
3. **Two-column split:** a 260 px filter panel (220 px below 1180 px) on the left; results flexible on the right.
   - **FilterPanel (P1, FR-U10):** dates (any upcoming / 30 / 90 days), event format, source, "Based on" (priorities / stated & confirmed / AI-inferred), and a **How ranking works** box ("Dots show relative relevance within this list, not a probability or eligibility"; "Expired items are hidden").
   - On ≤ 900 px the panel collapses to a single "Filters · Show filters" row.
   - In P0 only the tabs and sort exist; the panel is designed now so the layout doesn't change later.
   - **Results header:** "Showing n of N · sorted by relevance" + Sort select (Relevance · Date).
4. **OpportunityCard anatomy** (three columns: date tile | content | relevance and action):

   | Zone | Content |
   |---|---|
   | **DateTile** (left, top-aligned) | Label (DEADLINE / EVENT / PUBLISHED) + date (Manrope 16 bold) + relative time (mono). Teal outline when a deadline is ≤ 90 days away; "Not stated in source" variant when no date is known |
   | **Content** | Meta row (type chip · potential-match label for funding · source + retrieved date · data-status badge) → **title** (Manrope 17 bold) → type facts line (funder/purpose · format/location/audience · what changed) → **Why it matches** panel with cited claim chips ("Why it may matter" for inferred-only matches) |
   | **Side** | Rank (#n) + 5 relevance dots labelled "Relative relevance" (top); "Next step →" button (bottom) |

**States:** loading rows; empty per type ("No {type} findings for this profile in the {date} snapshot"); error.
**Responsive:** ≤ 900 px: the card is a single column; the date tile becomes a full-width inline strip at the top; rank and button form a footer row.

## S07. Finding Detail (P0)

**Purpose:** everything needed to judge and act. **Data:** the Match from the S06/S03 cache (Gap: DD-12).

**Layout (v2):**
1. **Breadcrumbs:** Findings / {type} / {short title}.
2. **Header card** (full width):
   - meta row: type, data status, "Rank #1" (no total, DD-22);
   - `h1` (30 px, max 28 ch);
   - source name + link;
   - primary "Open original source ↗" top right;
   - **KeyDateTiles** (four equal tiles): Deadline (teal, days left) · Funder (as stated) · Retrieved (snapshot) · Relevance (dots, "relative, not a probability"). Events use Starts · Format · Audience · Retrieved; updates use Published · What changed · Retrieved.
   - Full-width **PotentialMatchLabel band:** "Potential match. Eligibility not assessed. This compares the call with your public profile. Only the funder decides eligibility."
3. **Two-column split:**
   - **Main side:**
     - **Purpose**;
     - **Eligibility (as stated by the source)**: **one quoted text block** of `eligibility_summary`, never split into a list (DD-25), plus the note "Quoted from the source as collected. Not an assessment of your company";
     - **Why this matches you** (explanation + claim chips);
     - **Uncertainties**;
     - *(P1)* **SourceRecord**, an expandable `<details>` with: source, URL, retrieved timestamp, data status, language, and the original source text. These are only fields we already collect.
   - **Supporting panel (sticky):**
     - **NextStepPanel**: the next-step text in 16 px semibold; actions **Open original source** (primary, full width), **Ask the assistant about this**, *Save for later* (disabled, P1 note); a contact block "Need help applying? Blue Science Park staff can advise · Contact route pending verification · Simulated";
     - **Disclaimer card**.

**States:** not in cache → refetch matches → "This finding is no longer in your current results"; expired → a banner.
**Responsive:** ≤ 1180 px: the next-step panel moves **above** the main content, so the action stays near the top.

## S08. AI Innovation Assistant (P0)

**Purpose:** scoped help, with handling made visible, so it doesn't read like a generic chatbot.
**Data:** `POST …/ask` → `AssistantResponse`.

**Layout (v2):** header, then a two-column split: a **conversation card** (flexible) and a 360 px **context panel**.
1. **Conversation card:**
   - **Header strip:** "This session · private to {company} · follow-ups use the last 3 questions".
   - **Thread** (oldest → newest). The user's question appears as a right-aligned navy bubble (label "YOU", or "YOU · FOLLOW-UP"). Each reply is a **ResponseCard** with a colour-coded left rule, in separated zones:

     | Zone | Content | Shown for |
     |---|---|---|
     | Header | **HandlingBadge** + a static one-line explanation mapped from `handling` (never what data was used) ("Boundary applies to follow-ups too", "Needs a human decision") | All |
     | Answer | 15 px text, max 76 ch | All |
     | Findings mentioned · Sources | Two columns: mini finding rows **only for citations whose URL matches an already-loaded finding** (title + date tile, links to S07) · numbered citations with domain and retrieved date | `in_scope` with citations |
     | Referral | ReferralCard (staff, route status, Simulated) | `needs_human` |
     | Suggestions | Chips from `suggested_questions` | `out_of_scope`, `unclear`, `boundary_override` |
     | ~~Next step~~ | **Removed in P0** (DD-24): not returned by `AssistantResponse`. Next steps live on findings and the detail page | — |
     | Disclaimer | Small footer | When opportunities are discussed |

   - **Composer** (sticky at the bottom of the card):
     - **P0:** "Examples": 3–4 static, team-written chips (DD-14). *(P1)* "Suggested for you" contextual templates;
     - AskBox with a send button;
     - hint "Enter to send · Shift+Enter for a new line" and a counter "0 / 500".
2. **Context panel** (sticky):
   - **What the assistant uses** (static, FR-I03): "your company profile, your current findings and the collected public sources". No counts or versions. The sentence "Other companies' profiles and questions are never used or shown" is shown only after T-26 passes;
   - **How I handle requests**: the 5 handling badges, each with a one-line explanation. This demonstrates the boundaries without filling the thread with test prompts;
   - **I can't**: eligibility decisions or commitments, legal or financial advice, other companies' information.

**Contextual suggestions (P1, DD-24):** client-side templates filled from the active company's own top findings and claims, e.g. "Summarise the requirements of {top funding title}", "Which {month} events fit {application area}?". These need no new endpoint and are labelled as suggestions ([DD-24](design-decisions.md)). API-provided `suggested_questions` appear only inside response cards.

**States:**
- Loading: the two real steps.
- Network error: inline alert + retry (the API itself fails closed).
- Empty: a scope note + suggestions only.

**Responsive (P1, DD-30):** ≤ 1180 px: the context panel moves below. ≤ 900 px: response zones stack into one column.

## S09. Connections (P2, design only)

**Purpose (future, FR-M12):** potential company-to-company connections, based only on public evidence.
**Layout:** a list of connection rows. Each row:
- the other company (public data only);
- "Shared basis": the overlapping *stated* claims of both companies, with sources;
- explanation;
- a fixed note: **"This is based on public information only. Neither company has expressed an interest in collaborating."** (brief p.3 item 5).

**Rules:** inferred or company-private claims are never used; nothing is visible to the other company. The screen appears disabled ("Planned") in the P0 prototype navigation.

## S10. Settings and Preferences (P2; feedback controls P1)

- **Monitoring interests:** in P0 these *are* profile priorities, edited in S05; this screen would only link there, avoiding a second source of truth (DD-10).
- **Notifications and digests:** P2 (FR-I14).
- **Feedback and saved items:** P1 (FR-M10).
- **My questions:** history list (FR-I13, P1).
- **Data and privacy:** what is private to the company, and how to request a profile reset (copy only).

## S11. Staff View (P2)

**Scope:** separate staff sign-in (future). The brief (p.2) says staff should be able to "identify opportunities, understand shared interests across members and support collaboration"; it is not in the p.1 prototype list.
**Layout concept:**
- ecosystem topics: counts of members per topic, from **stated and company-confirmed public claims only**;
- opportunities with the number of potentially matching members;
- no access to company-private data (corrections, questions, feedback) (BR-19).

**Design only;** no P0 implementation.

## S12. Sources and Transparency (P1)

Static page generated from [../sources.md](../sources.md) and [../handover.md](../handover.md):
- sources with access method and last retrieval;
- data-status definitions;
- what is simulated;
- known limitations;
- how the boundaries work.

It supports BR-14 and DLV-02 and is linked from the PrototypeBanner.

---

## Global States Checklist

| State | Pattern | Screens |
|---|---|---|
| Loading | Layout-matching skeletons; no spinners for whole pages | All |
| Empty | Icon + reason with dates + one action | 02–08 |
| Error | InlineAlert with what failed + retry; the rest of the page still works | All |
| Success | Toast with an action link (refinement impact) | 05 |
| Simulated | DataStatusBadge or SimulatedOverlay + banner | All |
| Expired | Hidden from lists; banner on direct detail | 06, 07 |
