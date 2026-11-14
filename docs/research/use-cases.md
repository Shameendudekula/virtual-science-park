# Use Cases

**Source:** [challenge-analysis.md](challenge-analysis.md), which summarises the official brief with page references. **Status:** Draft, pending team approval.

Priorities are defined in [requirements.md](../requirements.md), the single source of truth. **P0** = critical MVP, **P1** = should have, **P2** = could have / future work.

**Origin:** **Official** means the brief requires the behaviour (page reference given). **Example** means it appears only in the brief's example journey (p.4). **Team** means it is our proposal.

## Actors

| Actor | Source |
|---|---|
| Company user: a representative of one member company | Official (p.2 Who you're building for) |
| Other interested user: companies or people interested in the park's areas | Official (p.2); not separately served in the MVP |
| Blue Science Park staff | Official (p.2); in the MVP, the referral target for human decisions |
| Profiling agent, monitoring agents, matching agent, assistant | Team design ([architecture.md](../architecture.md)) |
| Jury | Team (demo audience) |

## Main User Journey

Based on the brief's example journey (p.4), adapted to our selected areas (D-014):

1. **Profile.** From the member list, the profiling agent reviews a member's website and creates a baseline profile. Each claim is labelled *stated* (with quote, link and retrieval date) or *inferred* (with rationale). Missing and uncertain information is flagged.
2. **Refine.** The company user corrects a claim (e.g. an application area) and adds a priority (e.g. "EU funding for maritime sensing").
3. **Discover.** The monitoring agents' collected funding calls, events and updates are ranked for this company. Each finding shows why it is relevant (citing profile claims), relevant dates, source link, retrieval date, data status, requirements or uncertainties, and a next step. The ranking changes after step 2.
4. **Ask.** The user asks a follow-up question in the ask-box. Unrelated questions, unclear questions, override attempts, requests for other companies' data, and questions needing a human decision are each handled as the brief requires.
5. **Compare (jury).** Switching between three members shows different findings for different profiles.

## Use Cases

| ID | Use case | Actor | Origin | Requirements | Priority |
|---|---|---|---|---|---|
| UC-01 | Generate baseline profiles for at least three members from the member list | Profiling agent | Official (p.1 Scope; p.2) | FR-P01–P07, FR-P11, FR-P13 | P0 |
| UC-02 | Review a profile: basis badges, evidence, retrieval dates, uncertainty flags, missing information | Company user | Official (p.1 Scope; p.2) | FR-P05, FR-P08, FR-P09, FR-U02, FR-U03 | P0 |
| UC-03 | Refine a profile: confirm, reject, edit, add, set priority | Company user | Official (p.1 Scope; p.4 step 2) | FR-P10, FR-P12, FR-U04 | P0 |
| UC-04 | Collect funding opportunities from a public source | Monitoring agent | Official (p.1 Scope; p.3 item 4) | FR-O01–O05, FR-O08, FR-O09 | P0 |
| UC-05 | Collect events and knowledge/trend updates from a public source | Monitoring agent | Official (p.1 Scope; p.2 item 1; p.3 item 2) | FR-O01–O04, FR-O06–O09 | P0 |
| UC-06 | View personalised findings with explanation, dates, source, next step and disclaimer | Company user | Official (p.1 Scope; p.3 item 6) | FR-M01–M09, FR-U05 | P0 |
| UC-07 | See findings change after refining the profile | Company user | Official (p.1 Scope; p.4 steps 2–3) | FR-M03 | P0 |
| UC-08 | Ask a relevant question and get a grounded answer with sources | Company user | Official (p.1 Scope bullet 7; p.3) | FR-I01–I03, FR-I09, FR-I11 | P0 |
| UC-09 | Ask an unrelated question: remit explained, redirected | Company user | Official (p.1 Scope bullet 7; p.3) | FR-I02, FR-I04 | P0 |
| UC-10 | Ask an unclear question: focused clarifying question | Company user | Official (p.3) | FR-I05 | P0 |
| UC-11 | Attempt to override boundaries or make the assistant adopt another role, including in a follow-up: declined | Company user | Official (p.1 Scope bullet 7; p.3) | FR-I06, FR-I07 | P0 |
| UC-12 | Ask for an eligibility decision, commitment or professional advice: referred to Blue Science Park staff | Company user | Official (p.3) | FR-I08, FR-I09 | P0 |
| UC-13 | Try to access another company's non-public profile data or interactions: refused | Company user | Official (p.3) | FR-I10, FR-S06, FR-S07 | P0 |
| UC-14 | Compare three companies' findings side by side | Jury | Team | FR-U09 | P1 |
| UC-15 | Save an opportunity and give feedback | Company user | Example (p.4 step 4); area 5 (p.3) | FR-M10, FR-M11, FR-U11 | P1 (save, feedback) / P2 (learning) |
| UC-16 | Enrich profiles from other public sources and keep them current from public member updates | Profiling agent | Official (p.1 Scope "where available"; p.3 item 5) | FR-P15, FR-P18, FR-P19, FR-O12 | P1 (other sources) / P2 (monitoring) |
| UC-17 | Add a new company by URL | Staff | Team | FR-P17, FR-S10 | P1 |
| UC-18 | Collaboration suggestions between members; staff view of shared interests | Company user, staff | Official (p.2; p.3 item 5); not selected | FR-M12, FR-U12 | P2 |
| UC-19 | Testing opportunities (testbeds, labs, pilots) | Monitoring agent | Official (p.3 item 3); not selected | FR-O13 | P2 |

Honesty labelling (BR-14) and treating external content as data (BR-17) apply to every use case. They are covered by FR-U07, NFR-02 and FR-S01–FR-S05.
