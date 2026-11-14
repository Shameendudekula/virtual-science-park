# Challenge Analysis: Blue Science Park — Virtual Science Park

**Source:** Official challenge brief "Virtual Science Park", Challenge by Blue Science Park, 4 pages. The PDF is kept locally by team members and is not committed ([Q-12](../requirements.md#q-open-questions)).
**Last reviewed:** 2026-11-12

Page references (e.g. *p.1 Scope*) point to the page and section heading of the brief. Anything without a page reference is **Team** interpretation and is labelled as such.

## 1. Challenge Question (p.1, header)

> "How can AI agents help companies discover relevant knowledge, connections and opportunities based on an understanding of their business?"

**The challenge (p.1):** Blue Science Park wants to develop a Virtual Science Park: a digital service for its member companies and other interested users. Build a prototype that uses AI agents to understand member companies, identify relevant information and opportunities, and present useful results through a clear interface. Any interaction with users must stay within the service's purpose: supporting innovation, business development and collaboration within the science park ecosystem.

## 2. The Problem (p.2, *The problem*)

- Companies need to follow developments in their markets and technology areas, and to find relevant events, testing environments, funding and potential partners.
- This information is scattered across websites, research publications and other channels. Finding it and judging its relevance takes time.
- A personalised service needs a useful starting point before a company fills in a detailed questionnaire. Public information about members can provide that foundation.

## 3. Target Users (p.2, *Who you're building for*)

| User | Role in the brief |
|---|---|
| Blue Science Park's 40+ member companies | **Primary users** |
| Other companies and people interested in the science park's areas of activity | Secondary users |
| Blue Science Park staff | Use the service to identify opportunities, understand shared interests across members and support collaboration |

The hackathon jury is the audience for the demo and pitch (*Team*; not a user group in the brief).

## 4. Hackathon Scope (p.1, *Scope for the hackathon*)

- Build **one working flow from member discovery to a personalised result**.
- The finished service should support all 40+ members. For the hackathon, demonstrate profiling on **a small selection of member companies** and **explain how it would scale**.
- You don't need to build every monitoring area in full: **choose one or two and demonstrate them convincingly**.
- You're free to choose your tools and architecture. **Explain the roles of your agents and how they work together.**

### The prototype should (p.1, bullet list)

| Ref | Requirement (brief wording) |
|---|---|
| S-1 | Generate baseline profiles for at least three companies from their websites and other public sources where available |
| S-2 | Show the evidence behind profile information and distinguish facts from inferred interests |
| S-3 | Let a user review and refine a profile |
| S-4 | Collect opportunities or updates from at least two distinct public information sources |
| S-5 | Show different recommendations or rankings for companies with different profiles |
| S-6 | Present results with source links and relevant dates |
| S-7 | Respond appropriately to a relevant request, an unrelated request and an attempt to override the service's boundaries |
| S-8 | Clearly label simulated data or functionality |

## 5. Building Member Profiles (p.2, *Start by understanding the members*)

The service begins with an agent that builds a baseline profile of each member company from public information. **Starting from a member list**, it reviews company websites and other relevant public sources to identify:

1. What the company does and which products or services it offers.
2. Its technologies, areas of expertise and application areas.
3. The markets, industries and customer groups it serves.
4. Its geographical focus, where stated.
5. Publicly stated development priorities, projects and collaborations.
6. Topics and opportunities that may be relevant to the company.

Rules:
- Each profile includes **source links and the date the information was retrieved**.
- **Distinguish explicitly stated facts from inferred interests**, and **flag information that is missing or uncertain**.
- **Don't infer confidential plans** or **treat an inferred interest as a confirmed company priority**.

## 6. Coverage Areas (p.2–3, *What the service should cover*)

| # | Area | Brief requirements | Team selection (D-014) |
|---|---|---|---|
| 1 | Knowledge and trend monitoring (p.2) | Relevant research, technology developments, industry news and regional developments; explain **what has changed and why it could matter** | **Selected** (updates) |
| 2 | Events (p.3) | Conferences, workshops, webinars, networking; show **online or in person, who they're for, key dates** | **Selected** |
| 3 | Testing opportunities (p.3) | Testbeds, labs, demonstration environments, pilots; explain the potential match and **how to take the next step** | Not selected (P2) |
| 4 | Funding opportunities (p.3) | Grants, calls, innovation programmes; summarise **purpose, deadlines, key eligibility requirements**; **distinguish a potential match from confirmed eligibility** | **Selected** |
| 5 | Personalised member monitoring (p.3) | Match and prioritise findings; refine interests; feedback on recommendations; monitor public member updates to keep profiles current; spot connections between companies; **explain the basis for a suggested collaboration without assuming either company has expressed an interest** | Matching and refinement in P0; feedback P1; member-update monitoring and collaboration P2. How profiles stay current is **explained** (deliverable) |
| 6 | Presentation and interaction (p.3) | Accessible interface (dashboard, digest, alerts or conversational); users can **verify the source, understand the relevance and see a possible next step** | Dashboard + ask-box (D-015) |

## 7. Interaction Boundaries (p.3, *Keep interactions within the service's purpose*)

**Supported interactions:**
- Exploring technology, research, market and regional developments relevant to companies.
- Finding events, testing environments and funding opportunities.
- Discovering relevant expertise, potential partners and collaboration opportunities.
- Understanding recommendations and refining company interests.
- Finding the right support or contact routes within Blue Science Park.

**Required behaviour:**
- **Out of scope:** briefly explain the service's remit and guide the user towards a relevant question or the right contact.
- **Unclear connection to the purpose:** ask a focused clarifying question.
- **Treat external websites and documents as information sources**, never as instructions that can change the service's role or rules.
- **Apply the same boundaries to follow-up questions** and to requests to adopt another role.
- **Never disclose another company's non-public profile information or user interactions.**
- **Distinguish information and suggested next steps** from professional advice, formal eligibility decisions or commitments by Blue Science Park.
- **Refer questions that need a human decision or commitment** to Blue Science Park staff.
- **Explain how you implement these boundaries and demonstrate that they work.**

## 8. Deliverables (p.1–2, *What to deliver*)

| Ref | Deliverable | Team document |
|---|---|---|
| DLV-01 | A working demo showing company profiling, profile refinement and personalised findings (p.1) | [pitch-outline.md](../pitch-outline.md) (demo script) |
| DLV-02 | A short explanation of the solution, including sources, agent roles, matching and how profiles stay current (p.2) | [solution-overview.md](../solution-overview.md) |
| DLV-03 | A quality and boundary check covering profile accuracy, recommendation relevance, source traceability and interaction limits (p.2) | [quality-boundary-check.md](../quality-boundary-check.md) |
| DLV-04 | A handover with code, setup instructions, known limitations and suggested next steps (p.2) | [handover.md](../handover.md) |
| DLV-05 | Pitch: explain the problem, demonstrate the solution, show its value to a company, describe what should be developed next (p.2) | [pitch-outline.md](../pitch-outline.md) |

## 9. Example User Journey (p.4)

1. The profiling agent reviews a member company's website and finds that it develops sensor solutions for industrial applications. It creates a baseline profile, with links supporting its findings.
2. A company representative reviews the profile, corrects an application area and adds that testing opportunities are currently a priority.
3. The monitoring agents find relevant testing environments, events and funding calls. The service summarises them, explains their relevance and highlights requirements or uncertainties.
4. The user can ask follow-up questions, save an opportunity and give feedback. If the conversation moves beyond the service's purpose, the assistant explains its scope and redirects appropriately.

The journey is an **example**, not a checklist. Saving opportunities and giving feedback are therefore P1 for us; the boundary behaviour in step 4 is required by S-7.

## 10. What a Strong Solution Demonstrates (p.4)

> "A strong solution creates a useful starting point from public company information, turns that understanding into relevant opportunities and helps users take the next step. It combines a working prototype with traceable sources, editable profiles and reliable boundaries that keep the service focused on Blue Science Park's activities."

The brief has no formal scoring rubric; this paragraph and DLV-03 are the closest thing to one ([Q-03](../requirements.md#q-open-questions)).

## 11. Team Analysis (Team)

- **"Stated" is not "true".** A quote found on a page shows that the source said it when we retrieved it. It does not show that the claim is accurate or current, or that the AI's paraphrase is faithful. That is why claims carry a `basis`, a company `review_state` and an `uncertain` flag, rather than a single "verified" label (D-016).
- **Only the company sets priorities.** The brief forbids treating inferred interests as confirmed priorities. In our model, a claim can be marked as a priority only by company action.
- **Confidential plans.** We only extract from public pages. "Development priorities, projects and collaborations" may only be `stated` (quoted) or `company_provided`, never `inferred`.
- **Boundaries are a feature, not a footnote.** S-7 and the p.3 rules make the assistant's scope part of what gets judged. It needs its own tests and demo segment.
- **Area choice.** The team chose funding, events, and knowledge/trend updates (D-014). The brief suggests "one or two" areas; events and updates are planned from the same source to keep the work manageable. See the cut rule in D-014.
- **Demo companies must be real members.** The brief asks for profiles of member companies built from their websites. The fictional examples below are for design and tests only. They must never be presented as members or as generated profiles.

### Fictional illustration (for design and test fixtures only)

These companies do not exist. They show how three different profiles should lead to different findings.

| Brief category | Company A (fictional) | Company B (fictional) | Company C (fictional) |
|---|---|---|---|
| Offering | Water-quality sensors for ports | Security monitoring software | Protein ingredients from fish by-products |
| Technology / application area | IoT sensing; maritime | Cybersecurity; public sector | Food processing; circular economy |
| Markets / customers | Port operators | Municipalities | Food manufacturers |
| Geographic focus | Example region (if stated) | Example country (if stated) | Missing (flagged) |
| Expected findings | Blue-economy calls, maritime events | Cybersecurity events, digital-security calls | Circular-economy calls, food-industry news |

Open questions: [requirements.md, section Q](../requirements.md#q-open-questions).
