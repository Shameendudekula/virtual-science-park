# Source Register

**Status:** Candidates only. **No source has been tested by the team.** Access methods below are what the source or third parties *report*; none is confirmed until it appears under "Test record" with a date. Do not describe any source as having a working API until it has been tested.

**Official requirement:** opportunities or updates from at least two distinct public information sources, presented with source links and relevant dates (BR-10, BR-12; brief p.1 Scope). The choice of sources is a **team decision** (the brief names none). Selected areas: funding, events, knowledge/trend updates (D-014).

## Data Status Definitions

| `data_status` | Meaning | UI label |
|---|---|---|
| `live` | Fetched from the source during this run | "Live · retrieved {date}" |
| `snapshot` | Stored earlier fetch of the real source | "Snapshot · retrieved {date}" |
| `seed` | Curated by hand from a real public source; the URL is real | "Seed data · retrieved {date}" |
| `simulated` | Invented for the demo | "Simulated — not a real opportunity" |

## Candidate Opportunity Sources

### S1: Vinnova: calls for proposals (funding)

| Field | Value |
|---|---|
| Source ID | `vinnova` |
| Area / type | Funding → `funding` |
| Base URL | https://www.vinnova.se/ |
| Reported access | Vinnova's open-data page reports open-data APIs (including a newer API following a shared standard for Swedish research funders, which requires an account and key) and CSV downloads. A calls endpoint `data.vinnova.se/api/utlysningar` is mentioned in older documentation. **Untested.** Fallback: public call pages as HTML |
| Reported terms | Vinnova states that its open data may be reused freely (CC0). **Pending verification** on the open-data page |
| Update frequency | Unknown. **Pending verification** |
| Planned status | `snapshot` (collected once per demo build) |
| Fields to map | title, purpose, deadline, eligibility summary, funder, URL |
| Language | Mostly Swedish |
| Test record | Not tested |

### S2: EU Funding & Tenders Portal (funding, alternative)

| Field | Value |
|---|---|
| Source ID | `eu_ft_portal` |
| Area / type | Funding → `funding` |
| Base URL | https://ec.europa.eu/info/funding-tenders/opportunities/portal/ |
| Reported access | Third-party guides describe a search endpoint used by the portal itself. No official documentation found. **Untested** |
| Reported terms | **Pending verification** (European Commission legal notice) |
| Update frequency | Unknown. **Pending verification** |
| Planned status | Fallback for S1 only; `snapshot` or `seed` |
| Language | English |
| Test record | Not tested |

### S3: Blue Science Park website: news and events (events, updates)

| Field | Value |
|---|---|
| Source ID | `bluesciencepark` |
| Area / type | Events → `event`; knowledge/trend updates → `update` |
| Base URL | https://www.bluesciencepark.se/ |
| Reported access | Public HTML pages. Location of news and event pages, and whether a feed exists, is unknown. **Untested** |
| Reported terms | Unknown; check site terms and `robots.txt`. Organiser approval recommended. **Pending verification** |
| Update frequency | Unknown. **Pending verification** |
| Planned status | `snapshot` |
| Fields to map | Events: title, format, audience, dates, location, URL. Updates: title, published date, what changed, URL |
| Language | Swedish and English |
| Test record | Not tested |

**Risks:**
- If S3 has too few current events or updates, event and update coverage needs another source. No such source has been identified or verified yet; add candidates here only after checking them.
- If S1 cannot be accessed, S2 is the funding fallback.

## Reference: Blue Science Park Contact Routes

Needed for out-of-scope redirects and staff referrals (FR-I04, FR-I08; brief p.3: "Finding the right support or contact routes within Blue Science Park", "Refer questions that need a human decision or commitment to Blue Science Park staff").

| Field | Value |
|---|---|
| Source | Public contact page on https://www.bluesciencepark.se/ (exact page **pending verification**) |
| Use | Referral text links to the public contact page only; no personal contact details are stored |
| Status | **Pending verification** ([Q-11](requirements.md#q-open-questions)). Until verified, referrals say "Blue Science Park staff (contact route pending verification)" and are labelled simulated |

## MVP Selection (proposal, pending decision)

| Priority | Sources | Covers |
|---|---|---|
| P0 | **S1** (funding) + **S3** (events, updates) | Two distinct sources; all three selected areas |
| Fallback | S2 instead of S1 | Funding |
| P1 | All three, with live refresh (FR-O11) | — |

## Verification Checklist (per source, before first use)

- [ ] Access tested from the venue network; endpoint or pages and fields recorded under "Test record"
- [ ] Terms of use and `robots.txt` checked and recorded
- [ ] Mapping to the `Opportunity` schema defined ([api-contract.md](api-contract.md#opportunity))
- [ ] Snapshot stored in `data/snapshots/` with `retrieved_at`
- [ ] Domain added to the fetch allowlist ([security-privacy.md](security-privacy.md#3-outbound-requests-and-ssrf))

## References Consulted (2026-11-12; not verified by testing)

- Vinnova, "Open data": https://www.vinnova.se/en/about-us/about-the-website/open-data/
- Vinnova, "New standardized data model…" (2024): https://www.vinnova.se/en/news/2024/06/new-standardized-data-model-makes-it-easier-to-access-data-from-government-research-funders
- EMDESK, "EU Funding & Tenders Portal API" (third party): https://www.emdesk.com/horizon-2020-horizon-europe-basics-guide/eu-funding-tenders-portal-api-guide
