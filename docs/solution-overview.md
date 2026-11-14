# Solution Overview

**Deliverable DLV-02.** The brief asks for "a short explanation of the solution, including sources, agent roles, matching and how profiles stay current" (p.2), and asks teams to "explain the roles of your agents and how they work together" and "explain how it would scale" (p.1).

**Status:** Planned design. Nothing here is implemented yet. Update this document as the build progresses, and mark each section *Implemented*, *Simulated* or *Planned*.

## What it does

A Virtual Science Park assistant for Blue Science Park members. It:
1. builds a baseline profile of each member from public information, showing what is stated on a source and what is inferred;
2. lets the company refine that profile;
3. ranks funding calls, events and knowledge/trend updates for that company, with source links, dates, explanations and next steps;
4. answers questions within the science park's purpose and redirects everything else.

## Sources

| Purpose | Source | Status |
|---|---|---|
| Member profiles | Member websites from the member list (other public sources where available: P1) | Planned; member list source open ([Q-02](requirements.md#q-open-questions)) |
| Funding | Vinnova calls (S1); EU Funding & Tenders Portal as fallback (S2) | Candidates, untested ([sources.md](sources.md)) |
| Events, updates | Blue Science Park website news and events (S3) | Candidate, untested |
| Staff referral | Blue Science Park public contact page | Pending verification |

## Agent roles and how they work together

| Agent | Role |
|---|---|
| **Profiling agent** | Reads member websites, drafts claims in the brief's six categories, and checks every quote against the page. Flags uncertain and missing information |
| **Monitoring agents** | Collect funding calls, events and updates from public sources into dated snapshots with type-specific fields |
| **Matching agent** | Scores items against each company's active claims (company priorities count most), explains why each item may be relevant, and adds a next step and disclaimer |
| **Assistant** | Answers ask-box questions using only the active company's context and public items. A scope guard handles unrelated, unclear, override and human-decision requests |

The agents communicate through stored records (profiles, snapshots, matches), not by calling each other. Code makes all trust decisions: claim basis, scores, access and scope. Details: [architecture.md](architecture.md#agents-and-how-they-work-together).

## Matching

- A deterministic score from topic-tag overlap and keyword similarity between the company's claims and each item.
- Weighting: company priorities > company-provided or confirmed claims > stated claims > inferred claims.
- The same profile always produces the same ranking, so differences between companies are explainable.
- The LLM writes only the explanation, from the claims that produced the score.
- Funding results are always labelled "Potential match — eligibility not assessed".

## How profiles stay current (planned, not built in the MVP)

- Re-profile each member on a schedule and on request; only changed pages (by content hash) are re-processed.
- New claims arrive unreviewed. Claims whose evidence disappears are flagged uncertain. Company-provided information is never overwritten.
- Public member news is monitored like any other source and can suggest profile updates for the company to accept.
- Each profile shows when it was last researched.

See [architecture.md](architecture.md#keeping-profiles-current-explained-not-built-p2).

## How it scales to 40+ members (planned, not built)

- The same agents run per member as a scheduled background batch: a few hundred page fetches per full refresh, rate-limited per host.
- Infrastructure changes: job queue, Postgres, real sign-in, and a staff view of shared interests across members.
- Measured run time and LLM cost per member from the demo set will be added here, and extrapolated with stated assumptions. **No figures yet.**

See [architecture.md](architecture.md#scaling-to-40-members-explained-not-built).

## Boundaries

How the boundaries are implemented: [security-privacy.md §7](security-privacy.md#7-interaction-boundaries). How they are demonstrated: [quality-boundary-check.md](quality-boundary-check.md#4-interaction-limits).

## What is simulated in the MVP

- Sign-in (per-company demo tokens).
- Opportunity data is collected once as dated snapshots, not refreshed live.
- Staff contact route, until verified.

Everything simulated is labelled in the UI.
