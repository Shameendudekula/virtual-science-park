# Pitch Outline and Demo Script

**Deliverables DLV-01 and DLV-05.** The brief asks for "a working demo showing company profiling, profile refinement and personalised findings" (p.1), and a pitch that will "explain the problem, demonstrate the solution, show its value to a company and describe what should be developed next" (p.2).

**Status:** Outline. Fill in once the demo works. Never show planned features as working.

## 1. Problem (from the brief, p.2)

- Companies need to follow developments and find events, testing environments, funding and partners.
- That information is scattered, and judging its relevance takes time.
- A personalised service needs a starting point before a company fills in a questionnaire. Public information can provide it.

## 2. Demo Script (DLV-01)

| Step | Show | Requirements | Fallback if live step fails |
|---|---|---|---|
| 1 | Member list → baseline profile for member A: stated claims with quotes, links and dates; inferred interests labelled; missing and uncertain flags | BR-02–BR-08 | Pre-generated profile, labelled with its generation date |
| 2 | Refine: correct a claim and add a priority | BR-09 | — |
| 3 | Findings for member A: funding (potential-match label, eligibility summary, deadline), event (format, audience, dates), update (what changed); explanation, next step, source and dates | BR-10, BR-12, BR-23–BR-26 | Snapshot data, labelled |
| 4 | Ranking changes after the refinement in step 2 | BR-09, BR-11 | — |
| 5 | Switch to members B and C: different findings | BR-11 | — |
| 6 | Ask-box: relevant question; unrelated question; override attempt; follow-up role switch; eligibility question → staff referral; request for another member's data | BR-13, BR-16–BR-22 | Recorded responses from [quality-boundary-check.md](quality-boundary-check.md) |
| 7 | Point out the labels: simulated sign-in, snapshot data | BR-14 | — |

## 3. Value to a Company

Fill in with concrete demo examples: time saved finding relevant calls and events, an editable starting profile without a questionnaire, and every claim traceable to its source. **Do not use numbers that were not measured.**

## 4. How It Works

Agents, matching, boundaries, keeping profiles current, scaling: summarise from [solution-overview.md](solution-overview.md).

## 5. Quality and Boundaries

Show the measured results from [quality-boundary-check.md](quality-boundary-check.md), including failures.

## 6. What to Develop Next

From [handover.md](handover.md#suggested-next-steps).

## Honesty Checklist (before presenting)

- [ ] Every simulated feature and data set is named as such
- [ ] No claim of eligibility, guaranteed funding or Blue Science Park commitment
- [ ] "Stated on source" never presented as "verified true"
- [ ] Every figure shown comes from a recorded measurement
- [ ] Demo members are real members, profiled only from public sources ([Q-02](requirements.md#q-open-questions))
