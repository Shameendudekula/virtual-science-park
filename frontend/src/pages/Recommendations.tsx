import { Bookmark, CheckCircle2, Compass, EyeOff, FileText, Lightbulb, RotateCcw, Target } from "lucide-react";
import { useMemo, useState } from "react";
import { useWorkspace } from "@/app/workspace";
import { Badge, Button, Card, Drawer, EmptyState, ErrorState, LoadingBlock, PageHeader, Tabs } from "@/components/ui/primitives";
import { ClaimTypeBadge, SourceLink, TierBadge } from "@/components/shared/badges";
import { CriteriaBreakdown, EvidencePanel, MatchedConcepts, Section, Uncertainty } from "@/components/shared/explain";
import { PriorityEditor } from "@/features/priorities";
import { useProfile, useRecAction, useRecommendation, useRecommendations } from "@/services/queries";
import type { Recommendation, Tier } from "@/types/api";
import { cn, formatDate } from "@/lib/utils";

const KIND_LABEL: Record<string, string> = {
  apply_funding: "Apply for funding", research_proposal: "Research proposal", attend_event: "Event", investigate_facility: "Test environment",
  join_programme: "Programme", contact_partner: "Potential partner", explore_technology: "Technology", form_consortium: "Joint application",
};
type StatusFilter = "active" | "saved" | "explored" | "dismissed";

export default function Recommendations() {
  const { companyId } = useWorkspace();
  const q = useRecommendations(companyId);
  const profile = useProfile(companyId);
  const act = useRecAction(companyId);
  const [status, setStatus] = useState<StatusFilter>("active");
  const [open, setOpen] = useState<number | null>(null);
  const items = useMemo(() => (q.data?.items ?? []).filter((r) => (status === "active" ? r.status === "open" || r.status === "saved" : r.status === status)), [q.data, status]);
  const counts = useMemo(() => {
    const all = q.data?.items ?? [];
    return { active: all.filter((r) => r.status === "open" || r.status === "saved").length, saved: all.filter((r) => r.status === "saved").length, explored: all.filter((r) => r.status === "explored").length, dismissed: all.filter((r) => r.status === "dismissed").length };
  }, [q.data]);

  if (q.isLoading) return <LoadingBlock rows={5} />;
  if (q.isError) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  const d = q.data!;
  const tiers: Tier[] = ["high", "medium", "later"];

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Stage 5 · Personalised recommendations" title="Recommendation Centre"
        description="Opportunities, technologies and partners combined into prioritised actions. Every item shows its criteria, evidence and what is uncertain." />

      <Card className="overflow-hidden">
        <div className="grid gap-0 lg:grid-cols-[minmax(0,1fr)_340px]">
          <div className="bg-gradient-to-br from-navy-900 to-navy-700 p-6 text-white">
            <div className="text-[12px] font-semibold uppercase tracking-wider text-teal-300">Executive summary</div>
            <h2 className="mt-1 text-[19px] font-semibold">{d.summary.headline}</h2>
            <ul className="mt-3 space-y-1.5 text-[14px] text-slate-200">{d.summary.bullets.map((b) => <li key={b} className="flex gap-2"><span className="text-teal-300">•</span>{b}</li>)}</ul>
            <p className="mt-3 text-[11.5px] text-slate-400">{d.summary.llm?.used ? "Wording assisted by an LLM; checked against the facts." : "Deterministic summary from application records (no LLM)."}</p>
          </div>
          <div className="space-y-2 p-5 text-[12.5px] text-ink-2">
            <div className="font-semibold text-ink">How ranking works</div>
            <p>{d.method.ranking}</p>
            {tiers.map((t) => <p key={t}><TierBadge tier={t} /> <span className="ml-1">{d.method.tiers[t]}</span></p>)}
          </div>
        </div>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_400px]">
        <div className="space-y-5">
          <Tabs<StatusFilter> label="Status" value={status} onChange={setStatus}
            items={[{ value: "active", label: "To do", count: counts.active }, { value: "saved", label: "Saved", count: counts.saved }, { value: "explored", label: "Explored", count: counts.explored }, { value: "dismissed", label: "Dismissed", count: counts.dismissed }]} />
          {items.length === 0 && <EmptyState title="Nothing here" description={status === "active" ? "All recommendations were explored or dismissed. Adjust priorities to surface more." : "No recommendations with this status."} />}
          {tiers.map((tier) => {
            const list = items.filter((r) => r.priority_tier === tier);
            if (!list.length) return null;
            return (
              <section key={tier} aria-labelledby={`tier-${tier}`}>
                <h2 id={`tier-${tier}`} className="mb-2 flex items-center gap-2 text-[13px] font-semibold uppercase tracking-wide text-ink-3"><TierBadge tier={tier} />{list.length}</h2>
                <ul className="space-y-3">
                  {list.map((r) => <RecCard key={r.id} r={r} onOpen={() => setOpen(r.id)} onAction={(a) => act.mutate({ recId: r.id, action: a })} busy={act.isPending && act.variables?.recId === r.id} />)}
                </ul>
              </section>
            );
          })}
        </div>
        <div className="space-y-6">
          {profile.data && <PriorityEditor companyId={companyId} priorities={profile.data.priorities} compact />}
        </div>
      </div>
      <RecommendationDrawer id={open} onClose={() => setOpen(null)} />
    </div>
  );
}

function RecCard({ r, onOpen, onAction, busy }: { r: Recommendation; onOpen: () => void; onAction: (a: "save" | "dismiss" | "explore" | "restore") => void; busy: boolean }) {
  return (
    <li>
      <Card className={cn("p-4 transition hover:shadow-[var(--shadow-lift)]", r.status === "dismissed" && "opacity-70")}>
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="font-mono text-[12px] text-ink-3">#{r.rank_position}</span>
          <Badge tone="brand">{KIND_LABEL[r.kind] ?? r.kind}</Badge>
          <Badge tone="neutral" title="Rank score (0–100) from the listed criteria">rank {Math.round(r.rank_score)}</Badge>
          {r.status === "saved" && <Badge tone="violet" icon={<Bookmark className="size-3" />}>Saved</Badge>}
          {r.status === "explored" && <Badge tone="green" icon={<CheckCircle2 className="size-3" />}>Explored</Badge>}
          {r.detail.opportunity?.deadline_at && <Badge tone="neutral">Deadline {formatDate(r.detail.opportunity.deadline_at)}</Badge>}
        </div>
        <button onClick={onOpen} className="mt-2 text-left text-[15px] font-semibold leading-snug text-ink hover:text-brand">{r.title}</button>
        {r.detail.why[0] && <p className="mt-1.5 text-[13px] text-ink-2"><span className="font-medium text-ink">Why: </span>{r.detail.why[0]}</p>}
        <p className="mt-1.5 text-[13px] text-ink-2"><span className="font-medium text-ink">Next: </span>{r.detail.next_step}</p>
        <div className="mt-3 flex flex-wrap gap-2">
          <Button size="sm" variant="subtle" icon={<FileText className="size-3.5" />} onClick={onOpen}>Why this?</Button>
          {r.status !== "saved" && r.status !== "dismissed" && <Button size="sm" variant="outline" icon={<Bookmark className="size-3.5" />} onClick={() => onAction("save")} disabled={busy}>Save</Button>}
          {r.status !== "explored" && r.status !== "dismissed" && <Button size="sm" variant="outline" icon={<CheckCircle2 className="size-3.5" />} onClick={() => onAction("explore")} disabled={busy}>Mark explored</Button>}
          {r.status !== "dismissed" ? <Button size="sm" variant="ghost" icon={<EyeOff className="size-3.5" />} onClick={() => onAction("dismiss")} disabled={busy}>Dismiss</Button>
            : <Button size="sm" variant="ghost" icon={<RotateCcw className="size-3.5" />} onClick={() => onAction("restore")} disabled={busy}>Restore</Button>}
        </div>
      </Card>
    </li>
  );
}

export function RecommendationDrawer({ id, onClose }: { id: number | null; onClose: () => void }) {
  const q = useRecommendation(id ?? undefined);
  const r = q.data;
  return (
    <Drawer open={id !== null} onClose={onClose} title={r?.title ?? "Recommendation"}>
      {q.isLoading && <LoadingBlock rows={4} />}
      {q.isError && <ErrorState error={q.error} onRetry={() => q.refetch()} />}
      {r && (
        <div className="space-y-6">
          <div className="flex flex-wrap gap-1.5"><TierBadge tier={r.priority_tier} /><Badge tone="brand">{KIND_LABEL[r.kind] ?? r.kind}</Badge><Badge tone="neutral">rank #{r.rank_position} · {Math.round(r.rank_score)}</Badge></div>
          <Section title="1 · What" icon={<Compass className="size-3.5" />}><p className="text-[14px] text-ink">{r.detail.what}</p></Section>
          <Section title="2 · Why it is relevant" icon={<Target className="size-3.5" />}><ul className="list-disc space-y-1 pl-5 text-[13.5px] text-ink-2">{r.detail.why.map((w) => <li key={w}>{w}</li>)}</ul></Section>
          <Section title="3 · Related capability or priority">
            {r.detail.capabilities.length === 0 ? <p className="text-[13px] text-ink-3">Driven by stage relevance and priorities rather than a single capability.</p> : (
              <ul className="space-y-2">{r.detail.capabilities.map((c, i) => (
                <li key={c.concept + i} className="text-[13px]"><span className="font-medium text-ink">{c.concept}</span>
                  <ul className="mt-1 space-y-1">{c.claims.map((cl) => <li key={cl.id} className="flex flex-wrap items-center gap-1.5 text-ink-2">{cl.label}<ClaimTypeBadge type={cl.claim_type} /></li>)}</ul>
                </li>))}
              </ul>
            )}
          </Section>
          <Section title="4 · Potential business value" icon={<Lightbulb className="size-3.5" />}><p className="text-[13.5px] text-ink-2">{r.detail.business_value}</p><p className="text-[11.5px] text-ink-3">Generated explanation based on the matched records — not a forecast.</p></Section>
          <Section title="Ranking criteria"><CriteriaBreakdown criteria={r.detail.criteria} note={`Tier rule: ${r.detail.tier_rule}`} /></Section>
          {r.detail.match && <Section title="Matching criteria of the underlying opportunity"><MatchedConcepts criteria={r.detail.match.criteria} /></Section>}
          {r.detail.technology && <p className="text-[13px] text-ink-2">Technology ring: <span className="font-medium">{r.detail.technology.ring}</span> — {r.detail.technology.ring_rule}</p>}
          <section><h4 className="mb-2 text-[13px] font-semibold uppercase tracking-wide text-ink-3">5 · Evidence</h4><EvidencePanel evidence={r.evidence ?? []} title="Supporting sources" /></section>
          <Uncertainty items={r.detail.uncertainties} />
          <div className="rounded-xl border border-brand-100 bg-brand-50/60 p-4 text-[14px]"><div className="text-[12px] font-semibold uppercase tracking-wide text-brand">7 · What to do next</div><p className="mt-1 text-ink">{r.detail.next_step}</p>
            {r.detail.opportunity && <div className="mt-2 flex flex-wrap gap-4 text-[13px]"><SourceLink href={r.detail.opportunity.source_url}>Official record</SourceLink>{r.detail.opportunity.apply_url && <SourceLink href={r.detail.opportunity.apply_url}>Application page</SourceLink>}</div>}
          </div>
        </div>
      )}
    </Drawer>
  );
}
