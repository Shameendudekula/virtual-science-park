# Team Roles

**Status:** Solo project. One developer is responsible for every area of the hackathon prototype.

| Area | Responsibilities | Main requirements |
|---|---|---|
| Data and backend | SafeFetcher and allowlist, source collectors (Vinnova funding, Blue Science Park news), normaliser, SQLite models, demo build script, REST API, company-scope enforcement | FR-P01–P03, FR-O*, FR-S04–S06, FR-S08, FR-S09 |
| Profiling and matching | Profile extraction and evidence checking, deterministic matcher, explanations (template fallback; the LLM adapter stays unconnected until a provider is approved) | FR-P04–P13, FR-M* |
| Assistant and boundaries | Scope guard, responder, injection defences, boundary tests | FR-I*, FR-S01–S03, FR-S07 |
| Frontend | Company selection, profile and refinement, findings, detail, assistant, honesty labels, accessibility | FR-U* |
| Deliverables | Solution overview, quality and boundary check, handover, pitch and demo | DLV-01–DLV-05 |

## Working Rules

- Work in small vertical slices, and keep the application runnable after each milestone.
- Run the relevant tests before every commit.
- Keep documentation in `docs/` in step with the implementation.
- Never commit secrets, private data or AI working notes; commit and push only after explicit review.

Scope and priorities: [requirements.md](requirements.md). Plan: [design/prototype-plan.md](design/prototype-plan.md).
