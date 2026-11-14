# Data sources

The registry is `backend/app/services/collectors/registry.py`. Adding a source = a registry entry + (optionally) a `Collector` subclass implementing `fetch_live()` and `ingest()`.

| Key | Source | Status | Collected |
|---|---|---|---|
| `vinnova` | Vinnova open-data API: `/api/ansokningsomgangar/{date}`, `/api/utlysningar/{date}` | **Integrated (live + snapshot)** | Public application rounds (title, description, purpose / who-can-apply / funding texts, dates, apply link) and call names |
| `bsp_members` | Blue Science Park member directory `/wp-json/wp/v2/medlem` | **Integrated** | Name, link, modified date of all 56 members |
| `bsp_news` | Blue Science Park posts `/wp-json/wp/v2/posts` | **Integrated** | Title, date, link of the 100 latest posts |
| `bsp_events` | Blue Science Park events `/wp-json/wp/v2/event` | **Integrated** | Title, publication date, link |
| `company_websites` | Official websites of the 7 profiled organisations | **Integrated (verifier)** | Re-fetches pages and checks each stored excerpt is still present |
| `ymner` | Ymner | **External link only** | Nothing |
| `eu_funding_tenders` | EU Funding & Tenders Portal | **Not activated** | Nothing |

## Provenance

Every opportunity and evidence record has a `provenance`:

- **live** — collected by a live run in this deployment;
- **snapshot** — loaded from `backend/app/seed/snapshots/*.json`, collected 2026-11-13 through the same collectors; never shown as live;
- **user** — entered by a company in its workspace.

The Data Sources page shows last attempt, last successful live collection, record counts, rejection reasons and errors per source. Refresh snapshots with `cd backend && python -m scripts.refresh_snapshots`.

## Vinnova validation rules

Derived from inspecting the real data (`services/collectors/vinnova.py`):

- `Publik != 1` → rejected (internal rounds).
- Placeholder English titles (`x`, `xx`, `NA`, `---`…) → Swedish title used and flagged; both placeholder → rejected.
- Closing dates before 2000 (e.g. `1900-01-01`) or far in the future are **not deadlines** (`placeholder_rejected`) and shown as "Not stated in source".
- Dates are Europe/Stockholm local time, stored in UTC.
- Rounds closed more than 120 days before collection are skipped; recently closed rounds are kept as context, shown as closed, and never recommended.
- `DagligAvlasning = 1` → flagged as rolling assessment.
- **Eligibility** is only the verbatim *who can apply* text; VSP never decides eligibility.
- **Contact persons (`KontaktLista`) are removed before storage.**
- Canonical record URL `https://data.vinnova.se/api/ansokningsomgangar/{dnr}`; the official apply link is kept separately.

The API sometimes returns truncated JSON or times out. Such runs are recorded as failed; existing data is kept.

## Blue Science Park

`robots.txt` allows crawling, but reuse rights for page content were not confirmed, so VSP collects **metadata only** and never stores page bodies or sends BSP content to an LLM. Posts are classified by title (testing facility / business programme / ecosystem news). Event metadata has no event date or venue: locations are labelled *inferred from the organiser (Karlskrona)*, and events published more than 120 days ago are flagged as possibly past.

## Company information

`backend/app/seed/companies/*.json` holds 79 source-stated claims: Ocean Harvesting, Cleura, Roxtec (full profiles) and BTH, Kiwa, DNV Cyber, NKT (partial). Each cites a page and a **verbatim excerpt**; all 79 were verified against the live pages on 2026-11-13, and the `company_websites` collector re-checks them. Team biographies were not used. Locations come only from explicit statements (e.g. "Headquarters Karlskrona, Sweden"); members without one are shown as "Blekinge ecosystem (location not verified)" and get no proximity credit.

## Ymner investigation (13 Nov 2026)

Recommended by the Blue Science Park partner for funding discovery. Findings:

- The site is a client-rendered application; `/feed`, `/rss` and `/terms` return the application shell, so no feed was found and the terms of use could not be read without running the app.
- The data API under `/api/` returns **HTTP 401 (authentication required)**. No public, documented API or export was found.
- `robots.txt` allows crawling, which is not permission to reuse data.

**Decision:** no automated collection. Ymner is a clearly labelled external link in the unified funding view, and a disabled `ymner` registry entry records why. If Ymner provides an API key or export, a collector can be added without other changes. Cross-source deduplication (`views.dedupe_funding`, normalised title + deadline) already merges duplicate listings while keeping every original link.

## Adding a source

1. Add a `SourceDefinition` (allowed hosts, licence note, `llm_allowed`).
2. Implement `fetch_live()` using `self.client()` (the SSRF-safe client) and `ingest()` (validate, then `upsert_opportunity` / `upsert_evidence`).
3. Register it in `services/collectors/runner.py`; optionally write a snapshot.
