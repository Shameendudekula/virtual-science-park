# Handover

**Deliverable DLV-04.** The brief asks for "a handover with code, setup instructions, known limitations and suggested next steps" (p.2).

**Status:** Draft skeleton. No code exists yet. The setup steps are **planned** and will be replaced with tested commands (T-34) before the handover.

## Code

| Path | Contents | Status |
|---|---|---|
| `backend/` | FastAPI app, agents, tests | Not started |
| `frontend/` | React app | Not started |
| `data/config/` | Member list, source configuration, topic taxonomy | Not started |
| `data/snapshots/` | Collected opportunity snapshots with retrieval dates | Not started |
| `docs/` | Documentation | Draft |

## Setup (planned; not yet tested)

```bash
# Backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env              # add your own LLM API key; never commit .env
python -m app.cli build-demo      # profile demo members, collect snapshots, compute matches
uvicorn app.main:app --reload

# Frontend
cd frontend && npm install && npm run dev

# Tests
cd backend && pytest
cd frontend && npm test
```

## Known Limitations

These are planned by design for the MVP. Confirm or extend the list after the build.

- Profiles cover a small selection of members (at least three), from their websites only. Other public sources are P1.
- Opportunity data is a dated snapshot, not live. Refresh is manual.
- Sign-in is simulated; demo tokens are not real authentication.
- "Stated" means the quote was found on the source when retrieved. It does not confirm current accuracy.
- Matching is keyword- and tag-based. Semantic matches can be missed.
- The ask-box keeps only the last 3 exchanges; it is not a full chat.
- The staff contact route is pending verification.
- Not selected: testing opportunities, collaboration suggestions, member-update monitoring, feedback-based ranking.
- Quality and boundary results apply only to the demo set ([quality-boundary-check.md](quality-boundary-check.md)).

## Suggested Next Steps

Fill in from the build experience. Starting points:

1. Scheduled re-profiling with claim diffs (FR-P18, FR-P19).
2. Live source refresh, plus more sources for events and testing opportunities (FR-O11, FR-O13).
3. Real authentication and a staff view of shared interests (FR-U12).
4. Feedback-based ranking and collaboration suggestions (FR-M11, FR-M12).
5. Scale-out as described in [solution-overview.md](solution-overview.md).
