# API / UI Consistency Notes

**Status:** Accepted rules for Phase 2 (D-019, 2026-11-12). Every P0 UI element must map to an existing field or endpoint in [../api-contract.md](../api-contract.md), or be derived on the client from data the UI already holds. **No API fields are added for P0.** Elements that do not meet this rule are removed or moved to P1.

Legend for the source column:

| Value | Meaning |
|---|---|
| **API** | A field returned by the API |
| **Derived** | Computed in the browser from API data already loaded; no assumptions about what the server did |
| **Static** | Fixed, team-written UI text |
| **Removed** | Not shown in P0 |
| **P1** | Deferred |

## Profile (S04/S05)

| UI element | Source | Rule |
|---|---|---|
| Basis badge, review state, priority, uncertainty + reason | API (`ProfileClaim`) | Rendered as returned; never inferred on the client |
| Evidence quote, link, retrieved date, page date, source type | API (`Evidence`) | P0: evidence opens **inline** under the claim; the side panel for a selected claim is P1 |
| Completeness "n of 6 categories documented" | Derived: `6 − missing_fields.length` | `relevant_topic` is never counted (FR-P09, D-020) |
| Missing-information panel | API (`missing_fields`) | Inferred claims in a missing category appear as "AI suggestion (inferred)", not as documentation |
| Review counts (confirmed, not reviewed, uncertain, rejected, replaced) | Derived from `claims` | |
| "Replaced an AI version (…)" | Derived via `supersedes_claim_id` | |
| Confirm, Reject, Edit, Add, Set or unset priority | API (`PATCH` / `POST` claims) | Always visible; no View/Review toggle (DD-09 amended) |
| Profile data-status label | API (`CompanyProfile.data_status`) | Always shown in the profile header |

## Findings and Detail (S03, S06, S07)

| UI element | Source | Rule |
|---|---|---|
| Rank | API (`Match.rank`) | Shown as **"#n"** only; no "of N" total |
| Relevance dots | Derived from `score`, relative within the loaded list | Label "Relative relevance"; never a percentage |
| Date tile and days left | API (`deadline` / `starts_at` / `published_at`, `date_unknown`) + client clock | "Not stated in source" when `null` |
| Type facts (funding, event, update fields) | API (`Opportunity`) | `null` → "Not stated in source" |
| Eligibility | API (`eligibility_summary`) | **One quoted text block**, labelled "As stated by the source — not an assessment of your eligibility". Never split into a list |
| Potential-match label, explanation, cited claims, uncertainties, next step, disclaimer | API (`Match`) | `next_step` exists on `Match`, so it is shown on findings and detail (not in assistant responses) |
| Data-status badge and retrieved date | API | On every finding, including dashboard cards and list rows |
| Finding detail | Derived: match from the cached `GET …/matches` list | Deep link or reload → refetch the list; if still missing → "no longer in your current results" (DD-12) |
| Impact of a refinement | Derived: compare ranks from two `GET …/matches` responses | P0: a toast ("n findings re-ranked") plus ↑/↓ markers on findings. The drawer is P1 |
| Filters (dates, format, source, based on) | Derived (client-side) | **P1.** P0 has type tabs (`type=` parameter) and a sort control only |
| Source record (expandable) | API (`Opportunity` fields) | P1 |
| Save, feedback | P1 endpoints | P1 |

## Assistant (S08), with `AssistantResponse` unchanged

| UI element | Source | Rule |
|---|---|---|
| Handling badge | API (`handling`) | Always first in a response card |
| One-line explanation next to the badge (e.g. "Needs a human decision") | Static, mapped from `handling` | Describes the category only, never what data was used |
| Answer | API (`answer`) | |
| Sources list | API (`citations[]`) | |
| "Findings mentioned" | Derived: a citation whose `url` equals the `source_url` of an **already-loaded** match | Shows that match's title and key date and links to S07. Unmatched citations appear only in the sources list. Nothing is fetched or guessed |
| Referral card | API (`referral`) | `route_status = pending_verification` → "Contact route pending verification" + Simulated label |
| Suggested questions inside a response | API (`suggested_questions`) | |
| Disclaimer | API (`disclaimer`) | Only when present |
| Per-response "context used" line | **Removed** | Not returned by the API |
| Per-response "Next step" / "What I can do instead" strip | **Removed** | Not returned by the API; covered by `answer` and `suggested_questions` |
| Example questions above the ask-box | Static (DD-14) | Contextual, profile-based templates are P1 (DD-24 amended) |
| Panel "What the assistant uses" | Static description of FR-I03 | No counts or versions. The sentence "Other companies' data is never used" is shown only after T-26 passes |
| Session thread | Client state | Cleared on company switch; the server keeps its own last-3 context |

## Company Switching and Simulated Sign-In

- The demo token for the selected company is held **in memory only**: never in the URL, `localStorage` or logs.
- On every switch, the client discards the profile, the matches cache, the assistant thread, any open dialogs or toasts, and the impact baseline, then reloads for the new company (FR-S06, FR-S07).
- The top bar always shows "Acting as {company} · Simulated sign-in". No UI or pitch text claims production-grade isolation until T-26 and T-30 pass.

## Assets

- Fonts (Manrope, Inter, IBM Plex Mono) are **self-hosted**, bundled with the application. No request goes to Google Fonts at runtime. The HTML mockup still uses Google Fonts; it is a design reference, not the application.
- Icons are bundled (Lucide); no icon CDN.

## Known API Gaps (Not Addressed in P0)

| Gap | P0 handling | Later option (needs approval) |
|---|---|---|
| No `GET …/matches/{match_id}` | Cached list + refetch | Add the endpoint |
| No sector or summary on `Company` | Company list shows name, domain and data status only | Add public fields |
| No structured "findings mentioned" or next step in `AssistantResponse` | Citation matching; no next-step strip | Optional fields |
