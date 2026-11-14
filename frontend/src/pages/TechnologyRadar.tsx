import { Cpu, Info, Lightbulb, Target, Users } from "lucide-react";
import { useMemo, useState } from "react";
import { useWorkspace } from "@/app/workspace";
import { Badge, Card, CardBody, CardHeader, EmptyState, ErrorState, LoadingBlock, PageHeader, Tabs } from "@/components/ui/primitives";
import { ClaimTypeBadge, RingBadge } from "@/components/shared/badges";
import { CriteriaBreakdown, EvidencePanel, Section, Uncertainty } from "@/components/shared/explain";
import { TechRadar } from "@/components/charts/TechRadar";
import { OpportunityDrawer } from "@/features/opportunity";
import { useTechnologies } from "@/services/queries";

type RelFilter = "all" | "core" | "adjacent" | "interest" | "industry";

export default function TechnologyRadar() {
  const { companyId } = useWorkspace();
  const q = useTechnologies(companyId);
  const [area, setArea] = useState<string>("all");
  const [rel, setRel] = useState<RelFilter>("all");
  const [selected, setSelected] = useState<string | null>(null);
  const [openOpp, setOpenOpp] = useState<number | null>(null);
  const items = useMemo(() => (q.data?.items ?? []).filter((t) => (area === "all" || t.area === area) && (rel === "all" || t.relation === rel)), [q.data, area, rel]);
  const current = items.find((t) => t.key === selected) ?? items[0];

  if (q.isLoading) return <LoadingBlock rows={4} />;
  if (q.isError) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  const d = q.data!;
  return (
    <div className="space-y-5">
      <PageHeader eyebrow="Stage 3 · Discover new technologies" title="Technology Radar"
        description="Which technologies matter for this company — and why. Rings are VSP's recommendations of attention, not objective maturity levels." />
      <div className="flex flex-wrap items-center gap-3">
        <Tabs label="Technology area" value={area} onChange={setArea} items={[{ value: "all", label: "All areas" }, ...d.areas.map((a) => ({ value: a, label: a }))]} />
        <Tabs<RelFilter> label="Relationship" value={rel} onChange={setRel}
          items={[{ value: "all", label: "Any link" }, { value: "core", label: "Core" }, { value: "adjacent", label: "Capability-adjacent" }, { value: "interest", label: "Interest" }, { value: "industry", label: "Industry" }]} />
      </div>
      {items.length === 0 ? <EmptyState title="No technologies for these filters" /> : (
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
          <Card>
            <CardHeader icon={<Cpu className="size-4" />} title="Radar" subtitle="Click a numbered point or a list entry. Dashed outline = interest-only link." />
            <CardBody>
              <TechRadar items={items} areas={d.areas} selected={current?.key} onSelect={setSelected} />
              <div className="mt-4 grid gap-2 sm:grid-cols-2">
                {d.rings.map((r) => <div key={r} className="rounded-lg bg-canvas p-2.5 text-[12px]"><RingBadge ring={r as "adopt"} /> <span className="ml-1 text-ink-2">{d.ring_definitions[r]}</span></div>)}
              </div>
            </CardBody>
          </Card>
          {current && (
            <Card>
              <CardHeader title={<span className="flex items-center gap-2">{current.name}<RingBadge ring={current.ring} /></span>} subtitle={`${current.area} · ${current.relation} link · score ${Math.round(current.score)}`} />
              <CardBody className="space-y-5">
                <Section title="What it is" icon={<Info className="size-3.5" />}>
                  <p className="text-[13.5px] text-ink-2">{current.description}</p>
                  <p className="text-[11.5px] text-ink-3">{current.description_source}</p>
                </Section>
                <Section title="Why it is relevant" icon={<Target className="size-3.5" />}>
                  <CriteriaBreakdown criteria={current.contributions.map((c) => ({ criterion: c.criterion, value: c.value, max: c.criterion === "Documented capability" ? 40 : c.criterion === "Capability adjacency" ? 30 : c.criterion === "Opportunity momentum" ? 20 : c.criterion === "Stated or inferred interest" ? 15 : 10, explanation: c.explanation }))} />
                  <p className="text-[12.5px] text-ink-3">Ring rule: {current.ring_rule}</p>
                </Section>
                {(current.core_claims.length > 0 || current.interest_claims.length > 0) && (
                  <Section title="Related company claims">
                    <ul className="space-y-1.5">{[...current.core_claims, ...current.interest_claims].map((c) => <li key={c.id} className="flex flex-wrap items-center gap-1.5 text-[13px]"><span className="text-ink">{c.label}</span><ClaimTypeBadge type={c.claim_type} /></li>)}</ul>
                  </Section>
                )}
                {current.applications.length > 0 && (
                  <Section title="Possible applications" icon={<Lightbulb className="size-3.5" />}>
                    {current.applications.map((a) => (
                      <div key={a.application} className="rounded-xl border border-line p-3 text-[13px]">
                        <div className="font-medium text-ink">{a.application}</div>
                        <div className="mt-1 text-ink-2">Builds on: {a.capability}{a.capability_claims.length ? ` (${a.capability_claims.join("; ")})` : ""}</div>
                        <div className="mt-1 text-ink-2">Potential benefit: {a.benefit}</div>
                        <div className="mt-1 text-[11.5px] text-ink-3">{a.basis} — {a.rationale}</div>
                      </div>
                    ))}
                  </Section>
                )}
                <Section title="Related opportunities">
                  {current.related_opportunities.length === 0 ? <p className="text-[13px] text-ink-3">None open and relevant in the collected data.</p> :
                    <ul className="space-y-1.5">{current.related_opportunities.map((o) => <li key={o.id}><button className="text-left text-[13px] text-brand hover:underline" onClick={() => setOpenOpp(o.id)}>{o.title}</button> <Badge tone="neutral">{o.relevance_score}</Badge></li>)}</ul>}
                </Section>
                {current.related_companies.length > 0 && (
                  <Section title="Ecosystem organisations with this technology" icon={<Users className="size-3.5" />}>
                    <div className="flex flex-wrap gap-1.5">{current.related_companies.map((c) => <Badge key={c.id} tone="neutral">{c.name} · {c.relation}</Badge>)}</div>
                  </Section>
                )}
                <div className="rounded-lg border border-brand-100 bg-brand-50/60 p-3 text-[13.5px]"><span className="font-semibold">Next step: </span>{current.next_step}</div>
                <p className="text-[12px] text-ink-3"><span className="font-medium">Technical maturity:</span> {current.maturity}</p>
                <Uncertainty items={current.uncertainties} />
                <EvidencePanel ids={current.core_claims.map((c) => c.evidence_id ?? 0).filter(Boolean)} title="Source references" />
              </CardBody>
            </Card>
          )}
        </div>
      )}
      <OpportunityDrawer id={openOpp} companyId={companyId} onClose={() => setOpenOpp(null)} />
    </div>
  );
}
