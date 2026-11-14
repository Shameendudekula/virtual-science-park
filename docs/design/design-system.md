# Design System

**Status:** Proposal for team approval ([DD-04](design-decisions.md), [DD-05](design-decisions.md)). Tokens are written to map directly onto a Tailwind CSS theme. No packages have been installed.

**Direction:** premium B2B SaaS with a Scandinavian, editorial calm:
- deep navy structure and warm off-white paper, with one restrained teal accent;
- strong typography, generous whitespace and few cards per screen;
- colour carries *meaning* (basis, status), not decoration.

## 1. Identity

### Name treatment

```text
◉ Virtual Science Park
  INNOVATION INTELLIGENCE
```

- **Wordmark:** "Virtual Science Park" in Manrope SemiBold, letter-spacing −0.01em, navy-900 on light surfaces or white on navy.
- **Descriptor:** "INNOVATION INTELLIGENCE" in Inter Medium, 11 px, uppercase, letter-spacing 0.12em, teal-700 (teal-300 on navy).
- **Prototype mark:** a small "Prototype" chip may follow the wordmark in the app shell.
- Not affiliated branding: the product must not use Blue Science Park's logo, colours or logotype ([DD-03](design-decisions.md)).

### Logo direction (proposal)

- **Concept: "lens and node".** An outlined circle (the lens: understanding a business) with a solid dot offset on its edge (a node: an opportunity or connection). It reads as "focused insight" and scales down to 16 px.
- **Geometry:** circle with a 1.75 px stroke on a 24 px grid; dot diameter 6 px at the 2 o'clock position; teal dot on a navy ring.
- **Avoid:** sails, waves, triangles and swooshes, to stay clearly distinct from the host organisation's identity; also brains, sparkles and robot imagery (generic "AI" clichés).
- **Deliverable for Phase 2:** a single SVG drawn from primitives (circle and dot). No illustration work is needed.

## 2. Colour

### Palette

| Token | Hex | Use |
|---|---|---|
| `ink-900` | `#0F1B2D` | Primary text; sidebar background |
| `ink-800` | `#16263D` | Sidebar hover; dark surfaces |
| `ink-700` | `#2E405C` | Strong secondary text |
| `ink-600` | `#4A5A72` | Secondary text |
| `ink-500` | `#5F6F86` | Muted text (minimum for text on white) |
| `ink-400` | `#76869E` | Input borders and other UI outlines that must meet 3:1 |
| `ink-300` | `#A9B6C8` | Muted text on navy; disabled icons |
| `ink-200` | `#C5CEDA` | Decorative dividers only |
| `ink-100` | `#E7EBF1` | Subtle fills; snapshot badge background |
| `paper` | `#F7F5F0` | App background (warm off-white) |
| `paper-sunken` | `#EFECE5` | Wells, table headers, code-like blocks |
| `surface` | `#FFFFFF` | Cards, panels, inputs |
| `line` | `#E4E0D7` | Card borders on paper (decorative) |
| `teal-700` | `#0E6B66` | Primary actions, links, active states |
| `teal-800` | `#0B5551` | Primary hover; *stated* badge text |
| `teal-500` | `#14958C` | Focus ring |
| `teal-300` | `#6FD1C7` | Accent on navy (active nav, descriptor) |
| `teal-50` | `#E6F4F2` | *Stated* badge background; selected rows |

### Semantic colours

| Meaning | Text | Background | Icon (Lucide) | Shape cue |
|---|---|---|---|---|
| **Stated on source** | `#0B5551` | `#E6F4F2` | `file-check-2` | Solid left rule on evidence |
| **AI-inferred** | `#7A4B00` | `#FBF0D9` | `lightbulb` (not `sparkles`, to avoid "AI magic" connotations) | Dashed outline |
| **Provided by you** (company) | `#3341A0` | `#E8EBF8` | `user-round-check` | Solid outline |
| **Uncertain** | `#A3410F` | `#FFFFFF` + rust border | `circle-alert` | Rust dotted underline on the claim |
| **Missing** | `ink-600` | `paper-sunken` | `circle-dashed` | Dashed placeholder row |
| **Priority** (company-set) | `#3341A0` | — | `flag` | Flag icon before the claim |
| Success | `#1C6B43` | `#E3F2EA` | `check` | — |
| Danger | `#A61B1B` | `#FBE7E6` | `octagon-x` | — |
| **Simulated data or feature** | `#7A2E6B` | `#F6E9F3` | `flask-conical` | Diagonal hatch on the badge |
| **Snapshot data** | `ink-700` | `ink-100` | `camera` | — |
| Live data (P1) | `#1C6B43` | `#E3F2EA` | `radio` | — |

**Rule:** meaning is never carried by colour alone. Every badge combines icon + text + colour, and the basis badges also differ in outline style (solid, dashed or outlined), so they work in greyscale and for colour-blind users (FR-U08).

### Measured contrast (WCAG 2.x formula, computed 2026-11-12)

| Pair | Ratio | Requirement |
|---|---|---|
| `ink-900` on `paper` | 15.86 | AA text ✔ |
| `ink-600` on `paper` | 6.43 | AA text ✔ |
| `ink-500` on `surface` | 5.12 | AA text ✔ |
| white on `ink-900` | 17.28 | AA text ✔ |
| `ink-300` on `ink-900` | 8.41 | AA text ✔ |
| `teal-700` on white / white on `teal-700` | 6.34 | AA text ✔ |
| `teal-300` on `ink-900` | 9.56 | AA text ✔ |
| Stated badge | 7.64 | AA text ✔ |
| Inferred badge | 6.55 | AA text ✔ |
| Company badge | 7.35 | AA text ✔ |
| Uncertain text on white | 6.32 | AA text ✔ |
| Simulated badge | 7.35 | AA text ✔ |
| Snapshot badge | 8.76 | AA text ✔ |
| `ink-400` border on white / paper | 3.70 / 3.40 | Non-text 3:1 ✔ |
| `teal-500` focus ring on white / paper | 3.68 / 3.38 | Non-text 3:1 ✔ |
| `ink-200` divider on white | 1.59 | Decorative only; never the sole boundary of an input |

## 3. Typography

| Role | Font | Fallback stack | Licence |
|---|---|---|---|
| Display & headings | **Manrope** (600, 700) | `ui-sans-serif, system-ui` | SIL OFL |
| Body & UI | **Inter** (400, 500, 600) | `ui-sans-serif, system-ui` | SIL OFL |
| Data (dates, IDs, scores, URLs) | **IBM Plex Mono** (400, 500) | `ui-monospace, SFMono-Regular` | SIL OFL |

**Self-hosted** with the application (font files bundled, e.g. via `@fontsource` packages) and loaded with `font-display: swap`. Never loaded from Google Fonts at runtime (DD-27). The HTML mockup still uses Google Fonts as a design reference only. Tabular numerals (`font-variant-numeric: tabular-nums`) are used for dates and ranks.

| Token | Size / line height | Weight | Use |
|---|---|---|---|
| `display` | 40 / 48 | Manrope 700 | Landing headline only |
| `h1` | 28 / 36 | Manrope 700 | Page title |
| `h2` | 22 / 30 | Manrope 600 | Section title |
| `h3` | 18 / 26 | Manrope 600 | Card title |
| `body-lg` | 16 / 26 | Inter 400 | Explanations, assistant answers |
| `body` | 14 / 22 | Inter 400 | Default UI text |
| `label` | 13 / 18 | Inter 500 | Form labels, table headers |
| `caption` | 12 / 16 | Inter 500 | Badges, metadata |
| `overline` | 11 / 16, +0.12em, uppercase | Inter 600 | Section eyebrows |
| `mono` | 12 / 18 | Plex Mono 400 | Dates, URLs, IDs |

Body text measure: 60–75 characters (`max-w-prose`) for explanations and quotes.

## 4. Spacing, Radius, Elevation, Layout

**Spacing:** 4 px base, using the Tailwind default scale. Common values: 4 · 8 · 12 · 16 · 24 · 32 · 48 · 64.
- Card padding: 24 (20 when compact; 28 for hero and detail header).
- Section gap: 32. Grid gutter: 24.

**Radius:**

| Token | Value | Use |
|---|---|---|
| `sm` | 6 px | Badges, chips |
| `md` | 10 px | Inputs, buttons |
| `lg` | 14 px | Cards, panels |
| `xl` | 20 px | Dialogs, the landing hero panel |
| `full` | — | Avatars, status dots |

**Shadows** (restrained; borders do most of the work):

| Token | Value |
|---|---|
| `shadow-card` | `0 1px 2px rgba(15,27,45,.06)` |
| `shadow-raised` | `0 4px 16px rgba(15,27,45,.08)` (hover, popovers) |
| `shadow-overlay` | `0 16px 48px rgba(15,27,45,.18)` (dialogs, drawers) |

**Layout (v2, Phase 1.5):**

| Token | Value | Notes |
|---|---|---|
| Desktop frame | 1440 × 1024 | Also verified at 1680, 1024 and 390 |
| `--sidebar` | 240 px | Hidden ≤ 900 px; replaced by a top tab bar |
| Top bar / banner | 64 px (sticky) / 36 px | |
| `--content-max` | **1440 px** | Main workspace is flexible up to this width, centred beyond it |
| `--pad` | 32 px · 24 px ≤ 1180 · 16 px ≤ 900 | Horizontal page padding |
| `--gap` | 24 px | Between all major blocks |
| `--rail` | 360 px · 330 px ≤ 1360 | Supporting panel in two-column layouts; stacks ≤ 1180 |
| Filter panel | 260 px · 220 px ≤ 1180 | Left column on Findings; collapses ≤ 900 |
| Text measure | 72–80 ch | Limit text width with `max-width` in `ch`, never with narrow fixed columns |

**Layout patterns:**
- **Split:** `grid-template-columns: minmax(0,1fr) var(--rail)`. Used on Profile, Detail and Assistant.
- **Split-left:** `260px minmax(0,1fr)`. Used on Findings.
- **Hero:** one card split into a flexible area and a 380 px side panel. Dashboard only.
- **Featured row:** `1.6fr 1fr`. Dashboard top matches.
- **Three equal columns:** Dashboard lists.
- Sticky supporting panels sit at `top: 88px`, and become static when stacked.

| Name | Width | Behaviour |
|---|---|---|
| Wide | > 1360 px | Full layout |
| Desktop | ≤ 1360 px | Rails narrow to 330 px; hero side panel 340 px |
| Laptop / tablet | ≤ 1180 px | Splits stack (supporting panel below; the next-step panel moves **above** on Detail); hero and featured row stack |
| Mobile | ≤ 900 px | No sidebar (top tab bar); single column everywhere; filters collapse; opportunity cards stack |

**P0 is desktop-first (≥ 1280 px, DD-30).** The ≤ 1180 and ≤ 900 behaviour is P1: P0 only has to avoid breaking at those widths. In the mockup these thresholds are implemented as **container queries** on the app frame, so the width simulator gives honest results. In React/Tailwind they map to the `@container` plugin or to the equivalent viewport breakpoints.

The experience is desktop-first. Below `md`, the core flows (profile, findings, assistant) must work, but the demo is shown at ≥ 1280 px.

## 5. Motion

| Token | Duration / easing | Use |
|---|---|---|
| `motion-fast` | 120 ms ease-out | Hover, press |
| `motion-base` | 200 ms cubic-bezier(.2,.8,.2,1) | Drawer, toast, badge change |
| `motion-emph` | 320 ms same curve | Rank-change highlight after refinement (one pulse) |

Respect `prefers-reduced-motion`: replace movement with instant changes. No looping animations and no typing effects. Assistant answers render when complete.

## 6. Component Styles

### Buttons (`md` radius, 40 px high; 32 px `sm` variant)

| Variant | Style | Use |
|---|---|---|
| Primary | `teal-700` fill, white text, hover `teal-800` | One per view: "Review profile", "Open source", "Ask" |
| Secondary | White fill, `ink-400` border, `ink-900` text | Secondary actions |
| Ghost | Transparent, `teal-700` text | Inline actions ("View evidence") |
| Danger | White fill, danger border and text | "Reject claim" (with confirm) |
| External link | Ghost + `external-link` icon; opens a new tab with `rel="noopener noreferrer"` | Source links |

Focus: 2 px `teal-500` ring with 2 px offset on every interactive element.

### Inputs

- 40 px high, white fill, `ink-400` 1 px border, `md` radius. Label above in `label` style; helper text in `caption` `ink-600`.
- Error: danger border plus message with icon.
- **Ask-box:** a multi-line textarea, 3 rows growing to 6, max 500 characters with a counter, `Enter` to send and `Shift+Enter` for a new line.

### Cards

- White, `line` border, `lg` radius, `shadow-card`. Header row: overline + title + right-aligned meta (dates, data status).
- Maximum of **6 cards** visible above the fold on any screen. Findings are full-width OpportunityCards in a single column, never multi-column card grids ([DD-07](design-decisions.md), [DD-22](design-decisions.md)).

### Navigation

- **Sidebar:** `ink-900` background; items 40 px, Inter 500 14 px, `ink-300` text. Active item: white text, `teal-300` 3 px left bar, `ink-800` background.
- **Top bar:** white, bottom `line` border; company switcher on the left, actions on the right.
- **Tabs** (finding types): underline style, active `teal-700` 2 px underline, counts in mono.

### Tables

- Used for the company list and staff views. Header in `paper-sunken`, `label` style; rows 48 px with `line` dividers; row hover `teal-50`.
- Numbers and dates right-aligned in mono.

### Badges and chips (`sm` radius, 22 px high, `caption` style, icon 14 px)

| Component | Variants |
|---|---|
| BasisBadge | Stated on source · AI-inferred · Provided by you |
| ReviewStateChip | Not reviewed · Confirmed · Rejected · Replaced |
| DataStatusBadge | Snapshot · Seed · Simulated · Live (P1) |
| TypeChip | Funding · Event · Update |
| HandlingBadge | Answered · Outside scope · Needs clarification · Request declined · Referred to staff |
| PotentialMatchLabel | "Potential match — eligibility not assessed" (funding only; always visible, never truncated) |

### Evidence components

- **EvidenceQuote:** quote in `body` italic with a 3 px `teal-700` left rule; below it, SourceLink (domain in mono plus external icon) and "Retrieved 12 Nov 2026" in mono `ink-600`.
- **InferenceRationale:** for inferred claims, "Why the AI inferred this", with a dashed amber left rule and no quote styling. It must not look like evidence.
- **UncertaintyFlag:** a rust `circle-alert` icon with the reason text ("Source is a third-party page").
- **MissingInfoPanel:** a dashed-border panel listing missing categories, each with an "Add information" action (review mode).

### Status indicators

- **Profile coverage:** "4 of 6 categories documented". This is a segmented bar of 6 equal segments, one per documentable category (`relevant_topic` excluded, D-020): filled teal if the category has an active stated or company-provided claim, dashed if missing. It is derived from `missing_fields`, not a score ([DD-08](design-decisions.md)).
- **Review progress:** "8 of 12 claims reviewed", shown as text plus a thin bar.
- **Relevance:** rank number (#1, #2…) plus a 5-dot relevance indicator derived from `score` quintiles. Never shown as a percentage ([DD-08](design-decisions.md)).

### Dialogs, drawers and notifications

- **Dialog:** `xl` radius, max-width 520, `shadow-overlay`, focus trapped, `Esc` closes. Used for reject-claim confirmation and edit-claim.
- **Drawer:** right side, 480 px. Used for the evidence list of a claim and the impact summary.
- **Toast:** bottom-right, 360 px, auto-dismiss after 6 s (paused on hover), with an action link. Success example: "Profile updated · 3 findings re-ranked · View changes".
- **Inline alerts:** info, warning and danger variants with icon and title, used for error states and the prototype notice.

### Loading, empty and error

- **Skeletons** match final layout shapes (rows, badges), shimmer disabled under reduced motion.
- **Assistant loading:** "Checking your question against the service's scope…" then "Preparing an answer from your profile and sources…". Both are real steps of the backend flow (FR-I02, FR-I03); no fake progress percentages.
- **Empty states:** an icon, a one-line explanation and one action. Copy states the real reason, e.g. "No event findings for this profile in the snapshot collected on 12 Nov 2026."
- **Error states:** what failed, what still works, and a retry. Never a blank screen.

## 7. Iconography

**Lucide** (ISC licence), outline, 1.5 px stroke, 20 px in UI and 16 px in badges, `currentColor`. One icon per meaning, used consistently (see the semantic table). No filled or duotone icon sets, and no emoji in product UI.

## 8. Tailwind Mapping (for Phase 2; not yet created)

```js
// tailwind.config.ts — theme.extend (proposal)
colors: {
  ink: { 900:'#0F1B2D', 800:'#16263D', 700:'#2E405C', 600:'#4A5A72', 500:'#5F6F86',
         400:'#76869E', 300:'#A9B6C8', 200:'#C5CEDA', 100:'#E7EBF1' },
  paper: { DEFAULT:'#F7F5F0', sunken:'#EFECE5' }, surface:'#FFFFFF', line:'#E4E0D7',
  teal: { 800:'#0B5551', 700:'#0E6B66', 500:'#14958C', 300:'#6FD1C7', 50:'#E6F4F2' },
  basis: { stated:'#0B5551', statedBg:'#E6F4F2', inferred:'#7A4B00', inferredBg:'#FBF0D9',
           company:'#3341A0', companyBg:'#E8EBF8' },
  uncertain:'#A3410F', success:{ DEFAULT:'#1C6B43', bg:'#E3F2EA' },
  danger:{ DEFAULT:'#A61B1B', bg:'#FBE7E6' }, simulated:{ DEFAULT:'#7A2E6B', bg:'#F6E9F3' },
},
fontFamily: { display:['Manrope','ui-sans-serif','system-ui'],
              sans:['Inter','ui-sans-serif','system-ui'], mono:['"IBM Plex Mono"','ui-monospace'] },
borderRadius: { sm:'6px', md:'10px', lg:'14px', xl:'20px' },
boxShadow: { card:'0 1px 2px rgba(15,27,45,.06)', raised:'0 4px 16px rgba(15,27,45,.08)',
             overlay:'0 16px 48px rgba(15,27,45,.18)' },
maxWidth: { content:'1440px' },
spacing: { sidebar:'240px', rail:'360px' },
```

Tailwind's own `teal` and `blue` palettes are overridden on purpose, so that off-palette utilities cannot slip in.
