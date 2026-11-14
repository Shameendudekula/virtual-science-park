# Figma Reference Guide

**Status:** No Figma file has been created. No Figma or design-tool integration was available in this environment. This guide explains how to build the file by hand from the specifications.

A static HTML/CSS visual reference (v2, Phase 1.5) for the five key screens is at [mockups/key-screens.html](mockups/key-screens.html). Open it locally in a browser.
- It uses the design tokens from [design-system.md](design-system.md), and all its content is **fictional or simulated** and labelled.
- The floating dashed plum toolbar at the bottom is **mockup control only**, not product UI. It switches screens and preview widths (1680 / 1440 / 1024 / 390) and toggles design notes.
- URL options: `?w=390` sets the preview width; `?mk=0` hides the toolbar for clean screenshots.

## 1. File Structure

| Figma page | Contents |
|---|---|
| `00 Cover` | Name, version, status "Proposal", legend for P0/P1/P2 |
| `01 Foundations` | Colour variables, text styles, spacing, radius, shadows, icon set |
| `02 Components` | Every component from [component-inventory.md](component-inventory.md), with variants |
| `03 Screens — P0` | Frames 02–08 |
| `04 Screens — P1/P2` | Frames 01, 09–12 (P2 frames tagged "Future") |
| `05 States` | Loading, empty, error, success and simulated variants of the key screens |
| `06 Flows` | Prototype links for the demo click path ([user-flows.md](user-flows.md#demo-click-path-p0)) |

## 2. Foundations Setup

1. **Variables → collection `color`:** create every token from [design-system.md §2](design-system.md#2-colour) with the exact hex. Add a `semantic` collection that aliases them (`basis/stated/fg` → `teal-800`, and so on).
2. **Text styles:** one per row of the typography table (`display`, `h1`… `mono`). Fonts: Manrope, Inter, IBM Plex Mono (Google Fonts, OFL).
3. **Number variables:** spacing (4–64), radius (`sm` 6, `md` 10, `lg` 14, `xl` 20).
4. **Effect styles:** `shadow-card`, `shadow-raised`, `shadow-overlay`.
5. **Layout grid style "App workspace":** applied to the main area (frame width minus the 240 px sidebar): 32 px side padding, 24 px gutter, content max 1440. Use the layout patterns in [design-system.md §4](design-system.md#4-spacing-radius-elevation-layout) (split with a 360 px panel, 260 px filter panel) as auto-layout frames, not as fixed column counts.
6. **Icons:** import Lucide via its official Figma community file or SVGs, at 20 px and 1.5 px stroke.

## 3. Component Building Rules

- Use **auto layout** everywhere; padding and gaps come only from spacing variables.
- Use variants rather than duplicates:
  - `BasisBadge` (stated / inferred / company);
  - `HandlingBadge` (5 values);
  - `DataStatusBadge` (snapshot / seed / simulated / live);
  - `Button` (primary / secondary / ghost / danger × default / hover / focus / disabled);
  - `ClaimRow` (view / review × stated / inferred / company × uncertain on/off).
- Use component properties for text and booleans (e.g. `showUncertainty`, `isPriority`).
- Name layers after the React components so developers can map them 1:1.

## 4. Frames

| Frame | Size | Build from |
|---|---|---|
| `02 Companies — Desktop 1440` | 1440 × 1024 | [S02](screen-specifications.md#s02-company-selection-p0) |
| `03 Dashboard — Desktop 1440` | 1440 × 1200 | [S03](screen-specifications.md#s03-dashboard-p0) |
| `04 Profile — Desktop 1440` | 1440 × 1600 | [S04](screen-specifications.md#s04-company-intelligence-profile-p0) |
| `05 Profile Review — Desktop 1440` | 1440 × 1600 | [S05](screen-specifications.md#s05-profile-review-and-refinement-p0-part-of-s04) |
| `06 Findings — Desktop 1440` | 1440 × 1300 | [S06](screen-specifications.md#s06-findings-discovery-p0-filter-panel-p1) |
| `07 Finding Detail — Desktop 1440` | 1440 × 1200 | [S07](screen-specifications.md#s07-finding-detail-p0) |
| `08 Assistant — Desktop 1440` | 1440 × 1300 | [S08](screen-specifications.md#s08-ai-innovation-assistant-p0) |
| Responsive checks | 1680 × 1050, 1024 × 768, 390 × 844 | All five key screens (see the mockup width switcher) |

## 5. Data Rules for Mockups

- Use only the fictional companies A, B and C from [../research/challenge-analysis.md](../research/challenge-analysis.md). Show a **"Fictional sample"** badge in each frame's header.
- Findings use the source name **"Example source"**, never a real funder or organiser on invented content. Show a **"Simulated"** DataStatusBadge.
- Dates in mockups are examples. Do not show invented counts as achievements (no "120 opportunities found this week").
- Never place a real company logo or a real person's photo in a frame.

## 6. Image-Generation Prompts (optional mood references)

These are for quick mood boards only. Generated images are **not** design specifications, may contain invented text, and must never be shown as product screenshots. Always add: *"No real company names or logos; placeholder text only."*

**Shared style suffix:** "Premium B2B SaaS web app, Scandinavian minimal aesthetic, warm off-white background #F7F5F0, deep navy sidebar #0F1B2D, restrained teal accent #0E6B66, Manrope headings and Inter body text, thin outline icons, generous whitespace, subtle 1px borders, small soft shadows, no gradients, no glassmorphism, no 3D, no stock photos, desktop 1440×1024, crisp UI screenshot style, placeholder text only, no real company names or logos."

1. **Dashboard:** "Dashboard of an innovation-intelligence workspace for one company: top bar with a company switcher and a small 'simulated sign-in' label, a thin prototype notice banner, a single wide card with three steps (profile coverage bar with 6 segments, review progress, matched findings), a ranked list of five findings with small type chips (Funding, Event, Update), dates in monospace and five-dot relevance indicators, and a right rail with three compact lists for events, deadlines and updates." + style suffix
2. **Company intelligence profile:** "Company profile page: summary paragraph labelled 'AI-generated summary', 6-segment coverage meter, legend of three badges (teal 'Stated on source', amber dashed 'AI-inferred', indigo 'Provided by you'), sections for products, technologies, application areas, markets, geographic focus, stated projects and relevant topics; each claim row shows an italic quote with a teal left rule, a source domain in monospace and a retrieved date; one dashed 'missing information' row; right rail lists missing categories and sources used." + style suffix
3. **Opportunity discovery:** "Findings list page with underline tabs 'All, Funding, Events, Updates' and counts, ranked rows with rank numbers in monospace, type chip, title, a facts line (deadline, 'Potential match' label, or event format and date), a one-line 'why it matches' sentence, five-dot relevance and a 'Next step' link; right rail card explaining how ranking works." + style suffix
4. **Opportunity detail:** "Detail page for a funding call: breadcrumb, title, a full-width amber-outlined band reading 'Potential match — eligibility not assessed', a key-facts card (funder, purpose, deadline, eligibility requirements as stated by source), a 'Why this matches you' section with claim chips, an 'Uncertainties' list, and a sticky right card 'Next step' with a teal 'Open original source' button and a disclaimer card." + style suffix
5. **AI assistant:** "Assistant page with a large ask box, four example-question chips, a thread of responses each starting with a status badge (teal 'Answered', grey 'Outside scope', amber 'Needs clarification', rust 'Request declined', indigo 'Referred to staff'), numbered source citations with domains and dates, and a right rail listing what the assistant can and cannot help with." + style suffix
6. **Company selection:** "Clean table of three member companies with name, website domain in monospace, data-status badge and an 'Open workspace' action; short intro text above and a note about simulated sign-in." + style suffix
7. **Profile review mode:** "Profile page in review mode: sticky teal-tinted bar with progress '4 of 12 reviewed' and filter chips; claim rows with inline actions confirm, edit, reject, set priority; a right drawer titled 'Impact on your findings' listing rank changes with up and down arrows." + style suffix

## 7. Handing Over to Development

- Export variables as JSON (or copy them from [design-system.md §8](design-system.md#8-tailwind-mapping-for-phase-2-not-yet-created)) for the Tailwind theme.
- Every frame links its spec section in the frame description.
- Mark P2 frames "Future — not in MVP" with a frame-level banner.
