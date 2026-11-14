# Matching methodology

All matching is deterministic and explainable. Every score in the UI is the sum of the criteria shown next to it. **Scores are heuristics, not probabilities.**

## 1. Concepts

`services/intelligence/taxonomy.py` defines three kinds of concept, each with English and Swedish terms and a *specificity* weight:

- **Technologies** (18, the radar items), e.g. Energy Systems & Storage, Cybersecurity, Advanced Materials.
- **Industries** (15), e.g. Energy, Maritime & Offshore, Health & Life Science.
- **Capabilities** (22), e.g. Offshore & subsea structures, Cable & pipe sealing systems, Cloud infrastructure (IaaS).

Generic words ("innovation", "sustainable", "system", "future") are deliberately **not** concepts, so sharing them never creates relevance. Terms use word boundaries and exclusions found during calibration ("cyber" does not match "cyber-physical"; "infrastructure" does not match "infrastructure-as-a-service").

## 2. Company profile

Concepts are extracted from each claim. Claim strength: source-stated 1.0 · company-provided 0.9 · confirmed inference 0.9 · unconfirmed inference 0.5 · rejected/outdated/corrected 0. An *interest* contributes technology and industry concepts, never capabilities.

**Enrichment rules** propose interests from facts (e.g. model-based control + simulation → interest in digital twins). An inference is skipped when source facts already cover it, is never re-created after a reviewer rejects it, records its rule, explanation and source claims, and can never modify a source fact (enforced in the database layer).

## 3. Opportunity relevance (0–100)

| Criterion | Max | How |
|---|---|---|
| Technology fit | 35 | Shared technology concepts × where found (title 1.0, purpose 0.85, description 0.8, programme 0.5) × company strength × specificity |
| Industry fit | 20 | Shared industry concepts, same weighting |
| Capability & need fit | 15 | Shared capability concepts, plus a *need* bonus (e.g. test environments for companies documenting prototype validation) only when the opportunity is also topically related |
| Priority alignment | 15 | Strongest match between company priorities and the category |
| Timeliness | 10 | Open > upcoming > closing soon > no deadline > placeholder; closed caps the score at 10 |
| Regional relevance | 10 | See §6 |
| Evidence availability | 5 | Full official record 5 · partial 3 · metadata only 1 |

Penalties: **domain mismatch** (−25, or −10 with a topical match) when the opportunity targets a specific industry absent from the profile; **broad overlap only** caps the score at 30 when no specific concept matches. Eligibility and funding texts are excluded from topic extraction.

Bands: strong ≥ 55 · moderate ≥ 35 (the "relevant" threshold) · weak ≥ 20 · low.

Reported separately, never merged into the score: **evidence quality**, **information completeness**, **eligibility** (always "not assessed by VSP", with the source text quoted when present).

## 4. Technology radar

Contributions: documented capability (≤ 40), capability adjacency from authored hypotheses (≤ 30), recorded interest (≤ 15), industry relevance (10), opportunity momentum (≤ 20). Rings:

- **Adopt** — documented link + open relevant opportunities + score ≥ 55
- **Trial** — capability link or recorded interest + score ≥ 35
- **Assess** — plausible link with limited evidence, score ≥ 20
- **Monitor** — industry-level relevance only

Rings are recommendations of attention, not maturity levels; maturity is shown as "not assessed".

## 5. Collaboration complementarity

A suggestion requires at least one **complementarity rule**: a documented *need* on one side and a documented *offer* on the other (e.g. offshore structures ↔ certified sealing; prototype validation ↔ testing & certification; control systems ↔ academic research). Interests alone cannot form a need or offer. Score = rules (≤ 78; × weaker side's strength × priority) + shared context (≤ 10) + joint open opportunities (≤ 12, more when the call text mentions multiple participants) + regional proximity (≤ 10). Similar companies with no fired rule get no suggestion. Every suggestion is labelled *potential* with a disclaimer.

## 6. Regional relevance

Scopes: Karlskrona ⊂ Blekinge ⊂ Sweden ⊂ Europe, plus International and Online, each with a basis — *stated in source text* or *inferred* (e.g. "published by Blue Science Park, Karlskrona", "Vinnova is Sweden's national agency"). Base values:

| Situation | Value |
|---|---|
| Online event | 6 — location never reduces relevance |
| Physical event / facility / programme in Blekinge, company in Blekinge | 9 (7 if location inferred) |
| …elsewhere in Sweden | 3 |
| …abroad | 1.5 |
| National or European / international funding | 6 — not penalised |
| Regional Blekinge programme | 9 |

The value is multiplied by the *Prefer the local Blekinge ecosystem* priority (Off 0.25 · Normal 0.75 · Important 1.0 · Top 1.25) and by a **topical gate** `min(1, topical fit / 25)`, so proximity never substitutes for relevance. Partner proximity: both verified in Blekinge 10 · both in Sweden 4 · location unverified 0, gated by rule strength.

## 7. Recommendations

Candidates: relevant open opportunities, technologies in Adopt/Trial that are not already core, partners with score ≥ 25, and joint applications (call text mentions multiple participants and both companies match it).

Rank (0–100) = stage relevance (40) + priority alignment (25) + urgency (15) + evidence strength (10) + actionability (10); −12 when the primary priority is set to Off.

Tiers: **High** — rank ≥ 55, evidence ≥ 6, not resting only on unconfirmed inferences · **Medium** — rank ≥ 42 · **Explore later** — the rest.

Changing a priority recomputes everything and returns a ranking diff (up / down / new / removed), shown in the UI.

## 8. Calibration notes

Calibrated by inspecting results for the three demo companies. Problems found and fixed: bare "manufacturing" made Sustainable Manufacturing a core technology for a wave-energy company; using SiC inverters counted as semiconductor expertise; "optimisation" mapped to Data Analytics; a call was classed as a testing facility because its purpose text mentioned testing; need-based fit shielded a food-systems call from the domain-mismatch penalty; results depended on the order companies were recomputed in; "DigIT Hub Sweden" was read as a venue; the word "validation" in an unrelated semiconductor test call counted as a topical match through the need-marker concept `prototype_validation` (need markers now only feed the need bonus); the focus page listed a medium-tier item above high-tier ones (it now orders by tier, then rank, like the Recommendation Centre).
