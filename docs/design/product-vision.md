# Product Vision

**Phase 1 design documentation.** Status: proposal for team review. Nothing here is implemented.
**Authority:** The official brief, summarised in [../research/challenge-analysis.md](../research/challenge-analysis.md), overrides anything in this folder. Requirement IDs (BR-, FR-, DLV-) refer to [../requirements.md](../requirements.md).

How to read labels in this folder:

| Label | Meaning |
|---|---|
| **Official** | Required by the brief (page reference given) |
| **Decided** | Accepted team decision in [../decisions.md](../decisions.md) |
| **Proposal** | A design proposal from this folder; needs team approval (see [design-decisions.md](design-decisions.md)) |
| **Assumption** | Something we assumed in order to design; listed for verification |

## Name

**Virtual Science Park: AI-Powered Innovation Intelligence** (name given by the team lead, 2026-11-12).

- "Virtual Science Park" is the name of the concept Blue Science Park describes in the brief (p.1). The descriptor "AI-Powered Innovation Intelligence" is ours.
- **Pending approval:** whether we may present the product under this name, and how it relates visually to Blue Science Park's own brand. We will not use Blue Science Park's logo or imitate its visual identity ([DD-03](design-decisions.md)).

## One-Sentence Vision

An **Innovation Intelligence Workspace** where each Blue Science Park member sees what the service knows about it, how it knows it, and what it should look at next. Everything is grounded in public sources, can be corrected by the company, and stays within the science park's purpose.

## The Problem (Official, brief p.2)

Companies need to follow developments in their markets and technologies, and to find relevant events, testing environments, funding and partners. This information is scattered, and judging its relevance takes time. A personalised service needs a starting point before a company fills in a questionnaire; public information can provide it.

## Who It Is For (Official, brief p.2)

| User | MVP experience |
|---|---|
| Member company representative (primary) | Full P0 experience: profile, refinement, findings, assistant |
| Other interested companies and people | Not separately served in the MVP (P2) |
| Blue Science Park staff | Referral target in the MVP. A staff view of shared interests is P2 ([screen-specifications.md](screen-specifications.md#s11-staff-view-p2)) |

## Product Pillars

These are the six differentiators from the design brief. Each is mapped to a visible UI element and an existing requirement.

| Pillar | What the user sees | Requirements |
|---|---|---|
| **A. Evidence-first intelligence** | Every claim has a basis badge, a quote, a source link and a retrieval date | BR-05, BR-06, FR-P05, FR-U02 |
| **B. Transparent AI** | Three visually distinct bases: *Stated on source*, *AI-inferred*, *Provided by you*; a "What we don't know yet" panel; uncertainty flags with reasons | BR-05, BR-07, FR-P08, FR-P09, FR-U03 |
| **C. Explainable matching** | "Why this matches" lists the exact profile claims behind each finding | BR-23 (brief p.3 item 6), FR-M04 |
| **D. Human-controlled intelligence** | Always-visible actions on the profile: confirm, reject, edit, add, mark priority; a toast and ↑/↓ markers show how findings moved | BR-09, FR-P12, FR-M03 |
| **E. Action-oriented recommendations** | Every finding ends with a *Next step* callout and a link to the original source | BR-23, FR-M05 |
| **F. Responsible assistant** | The ask-box shows how each question was handled (answered, redirected, clarified, declined or referred) | BR-13, BR-16–BR-22, FR-I01–I12 |

## What We Deliberately Do Not Build

These are excluded because the brief does not require them, they cannot be done honestly in three days, or they would show data we don't have:

- Charts or KPIs without real underlying data (e.g. "AI score trends", "funding won").
- Eligibility scores, success probabilities or "match %" presented as certainty. The score is shown as a relative rank aid only ([DD-08](design-decisions.md)).
- Chat history, avatars or a personality for the assistant.
- Notifications, alerts and digests (P2, FR-I14).
- Collaboration suggestions and the staff view (P2, FR-M12, FR-U12). Designed as future screens only.

## Success Criteria for the Demo

These follow the brief (p.1 Scope; p.4 *What a strong solution demonstrates*):

1. Three member profiles, each showing stated, inferred and missing information with sources and dates.
2. A refinement that visibly re-ranks findings.
3. Findings from two distinct public sources, with relevant dates, explanations and next steps.
4. Different top findings for different members.
5. Correct assistant handling of relevant, unrelated and override requests, plus a follow-up, an unclear question and a staff referral.
6. Every simulated element labelled.

## Facts, Proposals and Assumptions in This Folder

| Item | Type |
|---|---|
| Required capabilities, selected areas, ask-box, claim model | Official / Decided |
| Visual identity, screens, components, layout | Proposal |
| Real member companies for the demo | **Assumption.** Not yet chosen ([Q-02](../requirements.md#q-open-questions)). All mockups use **fictional** companies, clearly labelled |
| Sources S1 (Vinnova) and S3 (Blue Science Park site) | **Assumption.** Untested ([../sources.md](../sources.md)). Mockups use a neutral "Example source" label, never a real funder's name on invented content |
| Product name usage | Pending approval ([DD-03](design-decisions.md)) |
