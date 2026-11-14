"""Company profile enrichment: transparent, rule-based inferences derived from source-stated claims.

Guarantees:
  * an inference never modifies or replaces a source-stated claim;
  * an inference is skipped when effective source-stated claims already cover what it would add;
  * a rejected inference is never silently re-created;
  * every inference records the rule, an explanation and the claims it was derived from.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import Company, CompanyClaim
from app.services.intelligence.concepts import label
from app.services.intelligence.profile import build_profile, claim_concepts, claim_strength


@dataclass(frozen=True)
class InferenceRule:
    key: str
    requires_all: tuple[str, ...]
    requires_any: tuple[str, ...]
    field: str
    label: str
    value: str
    explanation: str


INFERENCE_RULES: tuple[InferenceRule, ...] = (
    InferenceRule(
        "digital_twin_interest", ("control_algorithms", "simulation_modelling"), (), "research_interest",
        "Digital twins for model calibration and monitoring",
        "Likely interest in digital twins and virtual commissioning: the company combines model-based control with simulation-driven development.",
        "Inferred because the profile documents both {requires}. Model-based control and simulation models are the usual starting point for a digital twin.",
    ),
    InferenceRule(
        "ml_forecasting_interest", ("control_algorithms",), ("renewable_energy", "energy_systems"), "research_interest",
        "Machine learning for short-term forecasting",
        "Possible interest in machine learning for short-term forecasting of the inputs that predictive control reacts to.",
        "Inferred because predictive control ({requires}) in an energy context ({any}) benefits from forecasts of upcoming inputs.",
    ),
    InferenceRule(
        "energy_storage_interest", ("grid_integration",), ("renewable_energy",), "interest",
        "Energy storage and grid flexibility",
        "Likely interest in energy storage and grid flexibility services.",
        "Inferred from documented {requires} in a renewable-energy context ({any}).",
    ),
    InferenceRule(
        "digital_twin_bim_interest", ("engineering_software",), ("manufacturing_industry", "maritime_offshore", "construction_infrastructure"), "research_interest",
        "Digital twins / BIM integration of engineering data",
        "Possible interest in digital twins and BIM integration, since engineering software already manages design and installation data.",
        "Inferred because the profile documents {requires} serving {any} customers, where asset digital twins are increasingly requested.",
    ),
    InferenceRule(
        "condition_monitoring_interest", ("sealing_systems", "certified_products"), (), "interest",
        "Condition monitoring of safety-critical components (IIoT)",
        "Possible interest in condition monitoring (industrial IoT) for safety-critical components that are otherwise inspected and documented manually.",
        "Inferred because the profile documents {requires}: safety-critical products where inspection and documentation are mandatory.",
    ),
    InferenceRule(
        "edge_ai_interest", ("cloud_iaas", "ai_platform"), (), "research_interest",
        "Edge AI and edge-to-cloud services",
        "Possible interest in edge computing and edge AI as an extension of cloud and AI inference services.",
        "Inferred because the profile documents both {requires}; edge deployment is a common extension for customers with on-site data.",
    ),
    InferenceRule(
        "data_analytics_interest", ("ai_platform",), (), "interest",
        "Data platforms and analytics services",
        "Possible interest in data analytics and data platform services building on the AI platform.",
        "Inferred from documented {requires} and stated plans for data and AI building blocks.",
    ),
    InferenceRule(
        "defence_market_interest", ("data_sovereignty", "information_security_mgmt"), (), "industry",
        "Defence and public-sector customers",
        "Likely relevance of defence and public-sector customers with sovereignty requirements.",
        "Inferred because the profile documents {requires}, which are typical procurement requirements in defence and the public sector.",
    ),
    InferenceRule(
        "sustainable_manufacturing_interest", ("sustainability_reporting",), (), "interest",
        "Low-carbon and circular manufacturing",
        "Likely interest in low-carbon and circular manufacturing.",
        "Inferred from documented {requires}.",
    ),
)


@dataclass
class InferenceOutcome:
    rule: str
    label: str
    status: str  # created | exists | skipped_covered_by_source | skipped_rejected_by_user | not_applicable
    explanation: str


def _fmt(keys: tuple[str, ...]) -> str:
    return " and ".join(label(k) for k in keys) if keys else ""


def run_inference(db: Session, company: Company, *, dry_run: bool = False) -> list[InferenceOutcome]:
    profile = build_profile(company)
    # Only source-stated or user-provided facts may trigger inferences (no inference chains).
    factual = {
        k for k, s in profile.concepts.items()
        if any(c.claim_type in ("source_stated", "user_provided") and claim_strength(c) > 0 for c in s.claims)
    }
    stated_covered = {
        k for k, s in profile.concepts.items()
        if any(c.claim_type == "source_stated" and claim_strength(c) > 0 for c in s.claims)
    }
    outcomes: list[InferenceOutcome] = []
    by_rule = {c.inference_rule: c for c in company.claims if c.claim_type == "inferred" and c.inference_rule}
    for rule in INFERENCE_RULES:
        if not all(k in factual for k in rule.requires_all) or (rule.requires_any and not any(k in factual for k in rule.requires_any)):
            outcomes.append(InferenceOutcome(rule.key, rule.label, "not_applicable", "Required facts not present in profile."))
            continue
        any_hit = tuple(k for k in rule.requires_any if k in factual)
        explanation = rule.explanation.format(requires=_fmt(rule.requires_all), any=_fmt(any_hit))
        existing = by_rule.get(rule.key)
        if existing is not None:
            if existing.status == "rejected":
                outcomes.append(InferenceOutcome(rule.key, rule.label, "skipped_rejected_by_user", "A reviewer rejected this inference; it is not re-created."))
            else:
                outcomes.append(InferenceOutcome(rule.key, rule.label, "exists", explanation))
            continue
        candidate = CompanyClaim(field=rule.field, label=rule.label, value=rule.value, claim_type="inferred")
        new_concepts = set(claim_concepts(candidate))
        if new_concepts and new_concepts <= stated_covered:
            outcomes.append(InferenceOutcome(
                rule.key, rule.label, "skipped_covered_by_source",
                "Not added: source-stated facts already cover " + ", ".join(sorted(label(k) for k in new_concepts)) + ".",
            ))
            continue
        derived = sorted({c.id for k in (*rule.requires_all, *any_hit) for c in (profile.support(k).claims if profile.support(k) else [])
                          if c.claim_type in ("source_stated", "user_provided") and c.id})
        if dry_run:
            outcomes.append(InferenceOutcome(rule.key, rule.label, "pending_recompute", explanation))
            continue
        candidate.inference_rule = rule.key
        candidate.inference_explanation = explanation
        candidate.derived_from = derived[:8]
        candidate.status = "active"
        company.claims.append(candidate)
        db.flush()
        outcomes.append(InferenceOutcome(rule.key, rule.label, "created", explanation))
    return outcomes
