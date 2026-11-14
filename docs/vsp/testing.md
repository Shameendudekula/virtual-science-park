# Testing

## Backend (pytest, real PostgreSQL)

```bash
createdb -O vsp vsp_park_test          # once
cd backend && . .venv/bin/activate
pytest                                 # TEST_DATABASE_URL overrides the default test database
```

Each module rebuilds the schema with the Alembic migrations, then seeds from the bundled data. `REFERENCE_DATE` is pinned to 2026-11-13 (the snapshot date) so deadline-based assertions are reproducible.

| File | Covers |
|---|---|
| `test_matching.py` | Ocean Harvesting gets energy opportunities; Cleura gets cloud/cyber results; Roxtec gets industrial/materials results; the three get materially different results; irrelevant opportunities rank lower; shared keywords alone do not create relevance; broad overlap is capped; complementary capabilities create a suggestion and similarity alone does not; missing eligibility is communicated; scores are not presented as probabilities |
| `test_regional.py` | Locations come from cited claims; physical Karlskrona event beats the same event in Gothenburg; international webinar not penalised; European funding not disadvantaged; proximity never substitutes for relevance; the regional priority changes the weight; nearby complementary partner beats an identical one abroad; a distant but highly relevant partner is still recommended; a nearby company with only superficial similarity is not suggested; inferred locations are labelled |
| `test_profile_and_isolation.py` | Workspace access (401/403, forged tokens); password hashing and login; priority changes change the ranking; rejecting an inferred interest removes its influence and it is not re-created; source facts cannot be overwritten; inference skipped when covered by source facts; corrections preserve the original; private edits never leak to other companies; per-company search history |
| `test_collectors.py` | Vinnova validation (placeholders, non-public, invalid ids); personal data stripped; repeated collection creates no duplicates; changed records update in place; source failure and malformed payloads keep existing records; snapshots labelled as snapshots; disabled sources cannot run |
| `test_security_and_evidence.py` | SSRF guard (scheme, allowlist, IP literals, ports, credentials, DNS to private IPs, redirects, size limit); external content cannot change behaviour; LLM output that invents facts is rejected and grounded output accepted; works without an LLM key; every source-stated claim cites verified evidence; source links preserved; no invented deadlines; collaborations never presented as existing; evidence verifier detects changed pages; secrets redacted; membership verified from directory evidence |
| `test_api.py` | Health; error shape; security headers; admin token for collectors; no credentials exposed; pagination; member directory complete without duplicates; directory-only members get a clear error; brief as JSON and PDF; focus view compact and actionable; unified funding sources and dedup; natural-language search; recommendation actions company-scoped; login rate limit; demo reset |

Result on the build machine: **76 passed** (latest run: `76 passed, 2 warnings in 15.72s`).

## Frontend (Vitest + Testing Library)

```bash
cd frontend
npm test
npm run build      # tsc type-check + production build
```

| File | Covers |
|---|---|
| `components.test.tsx` | Claim-type labels; no invented deadlines; inferred/online location labels; regional explanation with basis; criteria breakdown with penalties; uncertainty dedup and empty state; empty and error states with retry; session store survives blocked storage and expires |
| `flows.test.tsx` | "Your Innovation Opportunities" renders explained actions, nearby partners and source links; API errors render without crashing; unreachable API message; automatic demo sign-in sends the bearer token; priority change sends weights and shows the ranking diff; Opportunity Radar renders ranked cards and applies the region filter; empty state when nothing matches |

Result on the build machine: **16 passed**.

## Manual verification performed

All workspace pages were loaded in headless Chromium against the running backend (desktop 1440 px and mobile 390 px) with no console errors and no horizontal overflow on mobile. Docker Compose was not executed because Docker is not installed on the build machine.
