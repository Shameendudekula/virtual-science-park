import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, patch, post, put } from "@/lib/api";
import type {
  Claim, Collaboration, CollectionRun, CompanyDetail, CompanySummary, Evidence, FocusResponse, FundingResponse, GraphResponse,
  Health, Member, Opportunity, OpportunityList, OverviewResponse, Page, ProfileResponse, RankingChange, Recommendation,
  SearchResponse, SourceInfo, TechItem, ExecSummary,
} from "@/types/api";

export const keys = {
  company: (id: number) => ["company", id] as const,
  workspace: (id: number) => ["workspace", id] as const,
};

export const useHealth = () => useQuery({ queryKey: ["health"], queryFn: () => api<Health>("/api/health"), staleTime: 60_000 });

export const useCompanies = (profiled = true) =>
  useQuery({
    queryKey: ["companies", profiled],
    queryFn: () => api<Page<CompanySummary>>(`/api/companies?page_size=100${profiled ? "&profile_level=profiled" : ""}`),
    staleTime: 5 * 60_000,
  });

export const useMembers = () => useQuery({ queryKey: ["members"], queryFn: () => api<{ items: Member[]; total: number; verified_members: number; profile_levels: Record<string, number>; note: string }>("/api/members") });

export const useCompany = (id?: number) =>
  useQuery({ queryKey: keys.company(id ?? 0), enabled: !!id, queryFn: () => api<CompanyDetail>(`/api/companies/${id}`) });

const ws = (id: number | undefined, part: string) => [...keys.workspace(id ?? 0), part] as const;

export const useFocus = (id?: number) => useQuery({ queryKey: ws(id, "focus"), enabled: !!id, queryFn: () => api<FocusResponse>(`/api/companies/${id}/focus`) });
export const useOverview = (id?: number) => useQuery({ queryKey: ws(id, "overview"), enabled: !!id, queryFn: () => api<OverviewResponse>(`/api/companies/${id}/overview`) });
export const useProfile = (id?: number) => useQuery({ queryKey: ws(id, "profile"), enabled: !!id, queryFn: () => api<ProfileResponse>(`/api/companies/${id}/profile`) });

export const useOpportunities = (id: number | undefined, params: URLSearchParams) =>
  useQuery({
    queryKey: [...ws(id, "opportunities"), params.toString()],
    enabled: !!id,
    queryFn: () => api<OpportunityList>(`/api/companies/${id}/opportunities?${params.toString()}`),
    placeholderData: (prev) => prev,
  });

export const useOpportunity = (oppId?: number, companyId?: number) =>
  useQuery({
    queryKey: ["opportunity", oppId, companyId],
    enabled: !!oppId,
    queryFn: () => api<Opportunity>(`/api/opportunities/${oppId}${companyId ? `?company_id=${companyId}` : ""}`),
  });

export const useFunding = (id?: number) => useQuery({ queryKey: ws(id, "funding"), enabled: !!id, queryFn: () => api<FundingResponse>(`/api/companies/${id}/funding`) });
export const useTechnologies = (id?: number) =>
  useQuery({ queryKey: ws(id, "technologies"), enabled: !!id, queryFn: () => api<{ items: TechItem[]; areas: string[]; rings: string[]; ring_definitions: Record<string, string>; note: string }>(`/api/companies/${id}/technologies`) });
export const useCollaborations = (id?: number) =>
  useQuery({ queryKey: ws(id, "collaborations"), enabled: !!id, queryFn: () => api<{ items: Collaboration[]; method: string }>(`/api/companies/${id}/collaborations`) });
export const useGraph = (id?: number) => useQuery({ queryKey: ws(id, "graph"), enabled: !!id, queryFn: () => api<GraphResponse>(`/api/companies/${id}/graph`) });
export const useRecommendations = (id?: number) =>
  useQuery({ queryKey: ws(id, "recommendations"), enabled: !!id, queryFn: () => api<{ items: Recommendation[]; summary: ExecSummary; method: { ranking: string; tiers: Record<string, string> } }>(`/api/companies/${id}/recommendations`) });
export const useRecommendation = (recId?: number) =>
  useQuery({ queryKey: ["recommendation", recId], enabled: !!recId, queryFn: () => api<Recommendation>(`/api/recommendations/${recId}`) });
export const useEvidence = (ids: number[]) =>
  useQuery({ queryKey: ["evidence", ids.join(",")], enabled: ids.length > 0, queryFn: () => api<Evidence[]>(`/api/evidence?ids=${ids.join(",")}`) });
export const useSources = () => useQuery({ queryKey: ["sources"], queryFn: () => api<SourceInfo[]>("/api/sources") });
export const useSourceHealth = () => useQuery({ queryKey: ["source-health"], queryFn: () => api<{ sources: SourceInfo[]; runs: CollectionRun[] }>("/api/sources/health") });
export const useNotifications = () =>
  useQuery({ queryKey: ["notifications"], queryFn: () => api<{ id: number; level: string; message: string; at: string; mode: string }[]>("/api/notifications"), staleTime: 60_000 });
export const useBrief = (id?: number) => useQuery({ queryKey: ws(id, "brief"), enabled: !!id, queryFn: () => api<BriefResponse>(`/api/companies/${id}/innovation-brief`) });
export const useCompare = (a?: number, b?: number) =>
  useQuery({ queryKey: ["compare", a, b], enabled: !!a && !!b && a !== b, queryFn: () => api<CompareResponse>(`/api/companies/compare?a=${a}&b=${b}`) });
export const useSearch = (q: string, companyId?: number) =>
  useQuery({ queryKey: ["search", q, companyId], enabled: q.trim().length >= 2, queryFn: () => api<SearchResponse>(`/api/search?q=${encodeURIComponent(q)}${companyId ? `&company_id=${companyId}` : ""}`) });
export const useSearchHistory = (enabled: boolean) =>
  useQuery({ queryKey: ["search-history"], enabled, queryFn: () => api<{ id: number; query: string; intent: string; result_count: number; created_at: string }[]>("/api/search/history") });

// --------------------------------------------------------------------- mutations
export interface DiffResponse { result: unknown; ranking_changes: RankingChange[] }

function useInvalidateWorkspace(id?: number) {
  const qc = useQueryClient();
  return () => {
    qc.invalidateQueries({ queryKey: keys.workspace(id ?? 0) });
    qc.invalidateQueries({ queryKey: keys.company(id ?? 0) });
  };
}

export function useSetPriorities(id?: number) {
  const invalidate = useInvalidateWorkspace(id);
  return useMutation({ mutationFn: (weights: Record<string, number>) => put<DiffResponse>(`/api/companies/${id}/priorities`, { weights }), onSuccess: invalidate });
}

export function useReviewClaim(id?: number) {
  const invalidate = useInvalidateWorkspace(id);
  return useMutation({
    mutationFn: ({ claimId, action, note }: { claimId: number; action: string; note?: string }) =>
      post<DiffResponse & { claim: Claim }>(`/api/companies/${id}/claims/${claimId}/review`, { action, note }),
    onSuccess: invalidate,
  });
}

export function usePatchProfile(id?: number) {
  const invalidate = useInvalidateWorkspace(id);
  return useMutation({
    mutationFn: (body: { add_claims?: { field: string; value: string; label?: string }[]; corrections?: { claim_id: number; value: string; note?: string }[] }) =>
      patch<DiffResponse>(`/api/companies/${id}/profile`, body),
    onSuccess: invalidate,
  });
}

export function useRecAction(id?: number) {
  const invalidate = useInvalidateWorkspace(id);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ recId, action }: { recId: number; action: "save" | "dismiss" | "explore" | "restore" }) => post<Recommendation>(`/api/recommendations/${recId}/${action}`),
    onSuccess: (_d, v) => {
      invalidate();
      qc.invalidateQueries({ queryKey: ["recommendation", v.recId] });
    },
  });
}

export function useRunCollector() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ key, mode }: { key: string; mode: "live" | "snapshot" }) => post<CollectionRun & { message: string }>(`/api/collectors/${key}/run?mode=${mode}`, undefined, { adminOnly: true }),
    onSuccess: () => qc.invalidateQueries(),
  });
}

export function useDemoReset() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: () => post<{ status: string }>("/api/demo/reset", undefined, { adminOnly: true }), onSuccess: () => qc.invalidateQueries() });
}

/** Whether the server accepts the admin token stored in this browser session (checked by the API, never guessed).
 * The token itself is never part of the query key. */
export const useAdminStatus = (hasToken: boolean) =>
  useQuery({ queryKey: ["admin-status", hasToken], enabled: hasToken, retry: false, staleTime: 0,
    queryFn: () => api<{ is_admin: boolean }>("/api/auth/me", { admin: true }) });

// --------------------------------------------------------------------- brief & compare
export interface BriefResponse {
  title: string; generated_at: string; as_of: string; company: { name: string; website: string | null; membership_status: string };
  executive_summary: ExecSummary;
  profile: { field: string; label: string | null; value: string; claim_type: string; evidence_id: number | null }[];
  opportunities: { id: number; title: string; organisation: string; score: number; band: string; deadline: string; why: string[]; eligibility: string; source_url: string; evidence_id: number | null }[];
  technologies: { name: string; ring: string; relation: string; next_step: string; application: string | null }[];
  partners: { name: string; strength: string; why: string[]; scenario: string; first_step: string }[];
  actions: { tier: string; title: string; next_step: string | null; rank_score: number }[];
  evidence: { id: number; title: string; publisher: string; url: string; retrieved_at: string; provenance: string; type: string }[];
  limitations: string[]; data_freshness: string;
}

export interface CompareResponse {
  a: { id: number; name: string; profile_level: string }; b: { id: number; name: string; profile_level: string };
  shared_capabilities: { key: string; label: string }[]; shared_technologies: { key: string; label: string }[]; shared_industries: { key: string; label: string }[];
  only_a_technologies: { key: string; label: string; claims?: string[] }[]; only_b_technologies: { key: string; label: string; claims?: string[] }[];
  only_a_capabilities: { key: string; label: string; claims?: string[] }[]; only_b_capabilities: { key: string; label: string; claims?: string[] }[];
  complementarity: Collaboration | null; joint_opportunities: { id: number; title: string; a_score: number; b_score: number; requires_consortium: boolean }[];
  missing_information: { company: string; unknown_fields: string[] }[]; note: string;
}
