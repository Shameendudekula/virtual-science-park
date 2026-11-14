export type ClaimType = "source_stated" | "inferred" | "user_provided";
export type Tier = "high" | "medium" | "later";
export type Ring = "adopt" | "trial" | "assess" | "monitor";
export type GeoScope = "karlskrona" | "blekinge" | "sweden" | "europe" | "international" | "online";

export interface Page<T> { items: T[]; total: number; page: number; page_size: number }

export interface Evidence {
  id: number; title: string; publisher: string; url: string; retrieved_at: string; excerpt: string | null;
  evidence_type: string; provenance: string; reuse_note: string; verification_status: string; verified_at: string | null;
  source_key: string | null;
}

export interface Claim {
  id: number; field: string; label: string | null; value: string; claim_type: ClaimType; status: string;
  evidence_id: number | null; inference_rule: string | null; inference_explanation: string | null; derived_from: number[];
  superseded_by_id: number | null; reviewed_at: string | null; review_note: string | null; concepts: string[];
  influences_matching: boolean; evidence: Evidence | null;
}

export interface CompanyLocation { scopes: GeoScope[]; label: string; basis: string; verified: boolean; claim_ids: number[] }

export interface CompanySummary {
  id: number; slug: string; name: string; tagline: string | null; website: string | null; profile_level: string;
  organisation_type: string; membership_status: string; is_demo_company: boolean;
}

export interface CompanyDetail extends CompanySummary {
  legal_name: string | null; membership_evidence: Evidence | null; overview: string | null;
  stats: { claims: number; source_stated: number; inferred: number; user_provided: number; completeness_pct: number };
  location: CompanyLocation | null; view: "public" | "private";
}

export interface Criterion { key: string; label: string; value: number; max: number; explanation: string; matches: CriterionMatch[] }
export interface CriterionMatch {
  concept: string; label: string; opportunity_terms: string[]; opportunity_field: string; company_strength: number;
  company_claims: { id: number; label: string | null; claim_type: ClaimType; status: string }[];
}

export interface Geography {
  scopes: GeoScope[]; labels: string[]; basis: string | null; inferred: boolean; format: string; format_basis: string | null;
  relevance_label: string; explanation: string; company_location: string | null;
}

export interface Timeliness { status: string; days_left: number | null; label: string; recent?: boolean }

export interface Match {
  opportunity_id: number; relevance_score: number; relevance_band: "strong" | "moderate" | "weak" | "low";
  criteria: Criterion[]; penalties: { key: string; value: number; explanation: string }[]; reasons: string[];
  missing_information: string[]; timeliness: Timeliness;
  evidence_quality: { level: string; label: string; explanation: string };
  completeness: { score_pct: number; present: string[]; missing: string[] };
  eligibility: { status: string; text: string | null; note: string };
  business_value: string; next_action: string; requires_consortium: boolean; supporting_claim_ids: number[];
  is_actionable: boolean; geography: Geography; score_note: string;
}

export interface Opportunity {
  id: number; external_id: string; title: string; title_original: string | null; description: string | null;
  purpose_text: string | null; eligibility_text: string | null; funding_text: string | null; category: string;
  category_label: string; organisation: string; programme: string | null; source_key: string | null; source_name: string | null;
  source_url: string; apply_url: string | null; language: string; published_at: string | null; opens_at: string | null;
  deadline_at: string | null; deadline_status: string; rolling_assessment: boolean; decision_expected_at: string | null;
  provenance: string; retrieved_at: string; quality_flags: string[];
  concepts: { key: string; weight: number; field: string; terms: string[]; direct: boolean }[];
  geo_scopes: GeoScope[]; geo_basis: string | null; geo_inferred: boolean; event_format: string; format_basis: string | null;
  evidence_id: number | null; timeliness: Timeliness; match?: Match; evidence?: Evidence | null;
}

export interface OpportunityList extends Page<Opportunity> {
  relevant_threshold: number;
  facets: { categories: string[]; sources: string[]; technologies: string[]; industries: string[] };
}

export interface TechItem {
  key: string; name: string; area: string; description: string; description_source: string; score: number; ring: Ring;
  ring_rule: string; relation: "core" | "adjacent" | "interest" | "industry";
  contributions: { criterion: string; value: number; explanation: string }[];
  applications: { capability: string; capability_claims: string[]; rationale: string; application: string; benefit: string; basis: string }[];
  core_claims: ClaimRef[]; interest_claims: ClaimRef[];
  related_opportunities: { id: number; title: string; relevance_score: number; category: string; deadline_at: string | null }[];
  related_companies: { id: number; name: string; relation: string }[];
  uncertainties: string[]; next_step: string; maturity: string;
}
export interface ClaimRef { id: number; label: string | null; field?: string; claim_type: ClaimType; status: string; evidence_id?: number | null }

export interface CollabRule {
  rule: string; relation: string; strength: number; contribution: number; direction: string; seeker_id: number; provider_id: number;
  need: { concept: string; label: string; claims: ClaimRef[] }; offer: { concept: string; label: string; claims: ClaimRef[] };
  rationale: string; scenario: string; seeker_benefit: string; provider_benefit: string; first_step: string; basis: string;
}

export interface Collaboration {
  id: number; partner_id: number; score: number; strength: "strong" | "moderate" | "exploratory"; status: "potential";
  partner: { id: number; name: string; slug: string; website: string | null; profile_level: string; organisation_type: string; membership_status: string; description: string | null };
  location: CompanyLocation | null; proximity: { value: number; explanation: string };
  criteria: { criterion: string; value: number; max: number; explanation: string }[];
  core_capabilities: string[]; relevant_technologies: string[];
  complementary_capabilities: { partner_offers: string[]; company_offers: string[] };
  why: string[]; scenario: string; mutual_benefit: { for_company: string; for_partner: string }; rules: CollabRule[];
  shared_context: string[]; shared_opportunities: { id: number; title: string; company_score: number; partner_score: number; requires_consortium: boolean }[];
  evidence_claim_ids: number[]; missing_information: string[]; uncertainties: string[]; first_step: string; disclaimer: string;
}

export interface RecDetail {
  what: string; why: string[]; capabilities: { concept: string; claims: ClaimRef[] }[]; business_value: string;
  evidence_ids: number[]; claim_ids: number[]; uncertainties: string[]; next_step: string; summary?: string;
  criteria: { criterion: string; value: number; max: number; explanation: string }[]; tier_rule: string;
  match?: { relevance_score: number; relevance_band: string; criteria: Criterion[] };
  opportunity?: { id: number; title: string; category: string; organisation: string; deadline_at: string | null; source_url: string; apply_url: string | null; provenance: string };
  technology?: { key: string; name: string; ring: Ring; score: number; ring_rule: string };
  collaboration?: Collaboration; partner?: { id: number; name: string };
}

export interface Recommendation {
  id: number; company_id: number; fingerprint: string; kind: string; title: string; priority_tier: Tier; rank_score: number;
  rank_position: number; status: "open" | "saved" | "dismissed" | "explored"; status_changed_at: string | null;
  related_opportunity_id: number | null; related_company_id: number | null; related_technology_id: number | null;
  computed_at: string; detail: RecDetail; evidence?: Evidence[]; claims?: Claim[];
}

export interface ExecSummary { headline: string; bullets: string[]; generated_by: string; as_of: string; llm?: { used: boolean; reason: string } }

export interface RankingChange {
  fingerprint: string; id: number; title: string; change: "up" | "down" | "new" | "removed" | "tier";
  before: { position: number; tier: Tier; score: number } | null; after: { position: number; tier: Tier; score: number } | null;
}

export interface Priority { key: string; label: string; description: string; weight: number }

export interface ProfileResponse {
  company: CompanyDetail; groups: Record<string, Claim[]>;
  concepts: { key: string; label: string; kind: string; strength: number; interest_only: boolean; claim_ids: number[] }[];
  completeness: { score_pct: number; fields: { field: string; count: number; types: ClaimType[]; status: string }[]; unknown: string[] };
  priorities: Priority[];
  inference_rules: { rule: string; label: string; status: string; explanation: string }[];
  revisions: { id: number; action: string; claim_id: number | null; note: string | null; created_at: string; before: Record<string, unknown>; after: Record<string, unknown> }[];
  legend: Record<string, string>;
}

export interface OppCard {
  id: number; title: string; organisation: string; category: string; score: number; band: string; deadline_at: string | null;
  days_left: number | null; timeliness: string; geography: Geography; url: string; why: string[];
}
export interface PartnerCard {
  id: number; name: string; score: number; strength: string; location: CompanyLocation | null; proximity: string; why: string[]; first_step: string; website: string | null;
}

export interface FocusResponse {
  company: { id: number; name: string; location: CompanyLocation | null };
  time_saved: { opportunities_screened: number; sources: string[]; relevant: number; message: string };
  top_three: { id: number; title: string; tier: Tier; kind: string; status: string; why: string[]; next_step: string; source: { label: string; url: string } | null; geography: Geography | CompanyLocation | null }[];
  deadlines: OppCard[]; new_opportunities: OppCard[]; local_events: OppCard[];
  regional_partners: PartnerCard[]; wider_partners: PartnerCard[];
  technologies: { key: string; name: string; ring: Ring; next_step: string }[];
  saved: { id: number; title: string; kind: string }[]; saved_count: number; priorities: Priority[]; freshness: string;
}

export interface OverviewResponse {
  company: { id: number; name: string; tagline: string | null; website: string | null; membership_status: string; profile_level: string };
  summary: ExecSummary;
  profile: { claims_by_type: Record<ClaimType, number>; completeness: number; overview: string | null; pending_review: number };
  metrics: { relevant_opportunities: number; opportunities_considered: number; technologies_adopt_trial: number; potential_partners: number; high_priority_actions: number };
  top_opportunities: { id: number; title: string; score: number; band: string; category: string; timeliness: Timeliness; organisation: string }[];
  technologies: { key: string; name: string; ring: Ring; score: number; relation: string }[];
  partners: { id: number; name: string; score: number; strength: string; headline: string }[];
  top_recommendations: { id: number; title: string; tier: Tier; kind: string; rank_score: number; status: string }[];
  deadlines: { id: number; title: string; deadline_at: string; days_left: number | null; score: number }[];
  freshness: Freshness;
}

export interface Freshness {
  last_live_collection: string | null; last_collection_attempt: string | null; latest_record_retrieved_at: string | null;
  data_modes: string[]; label: string; sources: { key: string; name: string; status: string; data_mode: string; last_success_at: string | null }[];
}

export interface SourceInfo {
  key: string; name: string; publisher: string; source_type: string; base_url: string | null; description: string; license_note: string;
  enabled: boolean; collectable: boolean; llm_allowed: boolean; disabled_reason: string | null; allowed_hosts: string[];
  health: { status: string; data_mode: string | null; last_attempt_at: string | null; last_success_at: string | null; last_error: string | null; consecutive_failures: number; record_count: number };
}

export interface CollectionRun {
  id: number; source_key: string; mode: string; trigger: string; status: string; started_at: string; finished_at: string | null;
  fetched: number; created: number; updated: number; unchanged: number; rejected: number; rejection_reasons: Record<string, number>; error: string | null;
}

export interface GraphNode { id: string; type: "company" | "technology" | "opportunity" | "capability"; label: string; data: Record<string, unknown> }
export interface GraphEdge { id: string; source: string; target: string; kind: string; label: string; explanation: string; disclaimer?: string; rules?: string[] }
export interface GraphResponse { nodes: GraphNode[]; edges: GraphEdge[]; legend: Record<string, string>; disclaimer: string }

export interface SearchResult { type: "opportunity" | "company" | "technology"; id: number | string; title: string; score: number; band?: string; subtitle: string; why: string[]; source_url?: string; provenance?: string; company_id?: number }
export interface SearchResponse {
  query: { text: string; intent: string; company_id: number | null; company_name: string | null; concepts: { key: string; label: string; kind: string }[]; categories: string[]; notes: string[]; parser: string };
  results: SearchResult[]; count: number; note: string;
}

export interface Health {
  status: string; database: string; version: string; demo_mode: boolean; llm: { enabled: boolean; provider: string | null };
  admin_actions_enabled: boolean; today: string; counts: Record<string, number>;
}

export interface Member {
  id: number; name: string; slug: string; profile_level: string; organisation_type: string; membership_status: string;
  membership_url: string | null; membership_retrieved_at: string | null; membership_provenance: string | null;
  location: CompanyLocation; has_workspace: boolean; is_demo_company: boolean; website: string | null;
}

export interface FundingItem {
  id: number; title: string; organisation: string; programme: string | null; category: string; score: number; band: string;
  deadline_at: string | null; deadline_status: string; timeliness: Timeliness; eligibility: Match["eligibility"]; geography: Geography;
  source_name: string | null; provenance: string; url: string; apply_url: string | null; also_listed_by: { source: string; url: string }[];
}
export interface FundingResponse {
  items: FundingItem[]; relevant: FundingItem[]; note: string;
  sources: { key: string; name: string; integrated: boolean; reason: string | null; link: string | null; note: string }[];
}
