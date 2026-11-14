# Five-minute demo

**Message:** Virtual Science Park saves small companies time and helps them find opportunities they would otherwise miss — with evidence for every claim.

**Before you start:** the app is running (Docker → http://localhost:8080, or dev → http://localhost:5173) with `DEMO_MODE=true`.

- **Sign in as the company before presenting.** Password-free demo workspaces are read-only, so the priorities step below needs a password session: on the login page, sign in with username `ocean-harvesting` and the company password (`DEMO_COMPANY_PASSWORD`, kept by the team; never show it on screen). The read-only banner disappears once you are signed in.
- Opening another company's workspace while signed in asks before leaving your session; choose **Stay** during the demo.
- Optional clean start: *Settings → Reset demo workspace*. This needs the admin token entered in Settings; without it the reset is not offered.
- If you present after the snapshot's deadlines have passed, run *Collect live* on Data Sources (admin token in Settings) or set `REFERENCE_DATE=2026-11-13`.

## 0:00–0:30 · The problem (landing page)

"Blue Science Park has 50+ members, most of them small. A 15-person company has no one following funding calls, ecosystem news and potential partners. Generic AI gives plausible answers without sources. VSP reads public sources and shows its working." Point at the live counts. Click **See Ocean Harvesting's opportunities**.

## 0:30–1:15 · Your opportunities, then the profile

Focus page: "Three things to investigate, each with *why* and a *next step*. VSP screened 206 records; 6 are worth their time." Note the location (Karlskrona, Blekinge) and *Companies nearby that could help*.

Open **1 Company Intelligence**. Show the green *Source-stated* badges; click **Review evidence** on InfinityWEC — verbatim excerpt, link, retrieval date, "Excerpt verified". Point at the amber *Inferred* interests and the rule behind them, and the rule that was skipped because source facts already cover it.

## 1:15–2:00 · Regional and wider opportunities

**2 Opportunity Radar.** Open *Industrial flexible energy control with advanced digitalization*: reasons, matched concepts with the company claims behind them, criteria, "eligibility quoted from the source; VSP does not assess eligibility", and the regional note "National programme — not a disadvantage".

Switch to **Regional map**: the Blue Science Park marine test environment sits in Karlskrona; national and European calls sit further out but still rank high.

## 2:00–2:20 · Physical vs online

Explain using the criteria panel: a physical event in Karlskrona earns proximity credit, the same event elsewhere in Sweden less, an online webinar is never penalised, European funding is not penalised, and proximity only counts when the topic is relevant. (The test suite covers each case with synthetic records; the collected BSP metadata contains no online events, so the map's *Online* lane is honestly empty.)

## 2:20–2:40 · Technology Radar

**3 Technology Radar.** Click *Digital Twins* (Trial): it builds on documented model-predictive control and simulation; application and benefit are labelled as hypotheses; maturity "not assessed".

## 2:40–3:30 · Complementary companies

**4 Collaboration Graph.** Read the disclaimer. Click **Roxtec**: Ocean Harvesting documents subsea structures in harsh conditions; Roxtec documents certified cable and pipe sealing for offshore installations. Both verified in Karlskrona. Show the first step and the "potential — not a partnership" badge. Shared keywords alone never create a link; BTH and NKT appear for research and grid-connection reasons.

## 3:30–4:30 · Three practical recommendations, then change a priority

**5 Recommendations.** Read the executive summary. Open **Why this?** on the top item: what, why, capability, value, evidence, uncertainty, next step.

In *Your priorities* (requires the password session from *Before you start*; in a read-only demo the button is disabled), set **Find testing facilities → Top** and **Find new funding → Off**, click **Update recommendations**. The ranking diff shows test environments and Kiwa moving up and funding items dropping. "Priorities change the ranking through transparent rules — no black box."

## 4:30–5:00 · Value

**Innovation brief → Export PDF**: profile, opportunities, technologies, partners, actions, numbered source references and data limitations.

Close: **"Virtual Science Park transforms scattered innovation information into evidence-backed opportunities, meaningful connections, and actionable business decisions."**

## Likely judge questions

- *Is it live?* Data Sources shows each source's mode; **Collect live** on Vinnova refreshes it (admin token required).
- *Can a visitor change the demo?* No. Password-free demo sessions are read-only, enforced by the API; only the company's password session can edit its own data, and only the admin token can reset.
- *What happens to my questions in Ask VSP?* A demo visitor's questions are not stored. A signed-in company sees its own question history.
- *What if Vinnova is down?* The run is recorded as failed; existing data stays.
- *Does Cleura see Ocean Harvesting's edits?* No — private edits never leave a workspace.
- *Why not Ymner?* Its API requires authentication and no reuse terms were found, so it is linked, not scraped.
- Afterwards: *Settings → Reset demo workspace* (admin token required), or undo your priority change by hand.
