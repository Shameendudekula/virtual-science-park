import { Background, Controls, MarkerType, ReactFlow, type Edge, type Node } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { List, MapPin, Network, ShieldAlert } from "lucide-react";
import { useMemo, useState } from "react";
import { useWorkspace } from "@/app/workspace";
import { Badge, Card, CardBody, CardHeader, EmptyState, ErrorState, LoadingBlock, PageHeader, Tabs } from "@/components/ui/primitives";
import { ClaimTypeBadge } from "@/components/shared/badges";
import { CriteriaBreakdown, Section, Uncertainty } from "@/components/shared/explain";
import { useCollaborations, useGraph } from "@/services/queries";
import type { Collaboration as Collab, GraphEdge, GraphNode, GraphResponse } from "@/types/api";

const TYPE_STYLE: Record<GraphNode["type"], { bg: string; border: string; text: string; label: string }> = {
  company: { bg: "#0b1b33", border: "#0b1b33", text: "#ffffff", label: "Organisation" },
  technology: { bg: "#eff4ff", border: "#2a78d6", text: "#1c3f7a", label: "Technology" },
  opportunity: { bg: "#fff4ee", border: "#eb6834", text: "#7a2e0e", label: "Opportunity" },
  capability: { bg: "#ecfbf4", border: "#1baf7a", text: "#0d5a3e", label: "Capability" },
};
type Kind = GraphNode["type"];

function layout(g: GraphResponse, show: Record<Kind, boolean>): { nodes: Node[]; edges: Edge[] } {
  const visible = g.nodes.filter((n) => show[n.type] || n.data.focus);
  const ids = new Set(visible.map((n) => n.id));
  const focus = visible.find((n) => n.data.focus);
  const byType = (t: Kind) => visible.filter((n) => n.type === t && !n.data.focus);
  const ring = (list: GraphNode[], r: number, offset: number) =>
    list.map((n, i) => ({ n, x: Math.cos(offset + (i / Math.max(list.length, 1)) * Math.PI * 2) * r, y: Math.sin(offset + (i / Math.max(list.length, 1)) * Math.PI * 2) * r }));
  const pos = [
    ...(focus ? [{ n: focus, x: 0, y: 0 }] : []),
    ...ring(byType("technology"), 200, -Math.PI / 2.6),
    ...ring(byType("capability"), 300, -Math.PI / 5),
    ...ring(byType("company"), 390, -Math.PI / 2),
    ...ring(byType("opportunity"), 540, -Math.PI / 2.3),
  ];
  const nodes: Node[] = pos.map(({ n, x, y }) => {
    const s = TYPE_STYLE[n.type];
    return {
      id: n.id, position: { x, y }, data: { label: n.label },
      style: { background: s.bg, color: s.text, border: `1.5px solid ${s.border}`, borderRadius: n.type === "company" ? 12 : 999, fontSize: 13,
        fontWeight: n.type === "company" ? 600 : 500, padding: n.data.focus ? "10px 14px" : "6px 10px", width: n.type === "opportunity" ? 210 : n.data.focus ? 190 : 165,
        boxShadow: n.data.focus ? "0 0 0 4px rgba(37,99,235,.25)" : undefined },
      ariaLabel: `${s.label}: ${n.label}`,
    };
  });
  const edges: Edge[] = g.edges.filter((e) => ids.has(e.source) && ids.has(e.target)).map((e) => ({
    id: e.id, source: e.source, target: e.target, type: "straight", label: e.kind === "potential_collaboration" ? e.label : undefined,
    animated: e.kind === "potential_collaboration",
    style: e.kind === "potential_collaboration" ? { stroke: "#eb6834", strokeWidth: 2.2, strokeDasharray: "6 4" }
      : e.kind === "mentions" ? { stroke: "#cbd5e1", strokeWidth: 0.8, opacity: 0.6 } : { stroke: "#94a3b8", strokeWidth: 1.3 },
    labelStyle: { fontSize: 10.5, fill: "#7a2e0e" }, markerEnd: e.kind === "potential_collaboration" ? { type: MarkerType.ArrowClosed, color: "#eb6834" } : undefined,
  }));
  return { nodes, edges };
}

export default function Collaboration() {
  const { companyId } = useWorkspace();
  const graph = useGraph(companyId);
  const collabs = useCollaborations(companyId);
  const [view, setView] = useState<"graph" | "list">("list");
  const [show, setShow] = useState<Record<Kind, boolean>>({ company: true, technology: true, opportunity: true, capability: false });
  const [selected, setSelected] = useState<{ kind: "node"; node: GraphNode } | { kind: "edge"; edge: GraphEdge } | null>(null);
  const flow = useMemo(() => (graph.data ? layout(graph.data, show) : { nodes: [], edges: [] }), [graph.data, show]);
  const partnerFor = (companyNodeId: string) => collabs.data?.items.find((c) => `c${c.partner_id}` === companyNodeId);

  if (collabs.isLoading) return <LoadingBlock rows={4} />;
  if (collabs.isError) return <ErrorState error={collabs.error} onRetry={() => collabs.refetch()} />;
  const items = collabs.data?.items ?? [];
  const g = graph.data;
  const selectedPartner = selected?.kind === "node" ? partnerFor(selected.node.id) : selected?.kind === "edge" ? partnerFor(selected.edge.target) ?? partnerFor(selected.edge.source) : undefined;

  return (
    <div className="space-y-5">
      <PageHeader eyebrow="Stage 4 · Find collaboration partners" title="Potential partners"
        description="Companies whose documented capabilities complement yours. Shared keywords alone never create a suggestion." />
      <div className="flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50/60 px-4 py-3 text-[13px] text-ink-2">
        <ShieldAlert className="mt-0.5 size-4 shrink-0 text-amber-700" aria-hidden />
        <span>{g?.disclaimer ?? items[0]?.disclaimer ?? "Suggestions only: these are potential collaborations derived from public information, not existing or agreed partnerships."}</span>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Tabs label="View" value={view} onChange={setView} items={[{ value: "list", label: <span className="inline-flex items-center gap-1.5"><List className="size-3.5" aria-hidden />Recommended partners</span>, count: items.length }, { value: "graph", label: <span className="inline-flex items-center gap-1.5"><Network className="size-3.5" aria-hidden />Explore ecosystem</span> }]} />
        {view === "graph" && (
          <fieldset className="flex flex-wrap items-center gap-3 text-[13px]">
            <legend className="sr-only">Show node types</legend>
            {(Object.keys(TYPE_STYLE) as Kind[]).map((k) => (
              <label key={k} className="inline-flex items-center gap-1.5">
                <input type="checkbox" checked={show[k]} onChange={(e) => setShow((s) => ({ ...s, [k]: e.target.checked }))} className="size-4 accent-[var(--color-brand)]" />
                <span className="size-3 rounded-full border-2" style={{ background: TYPE_STYLE[k].bg, borderColor: TYPE_STYLE[k].border }} />{TYPE_STYLE[k].label}
              </label>
            ))}
            <span className="inline-flex items-center gap-1.5 text-ink-3"><span className="h-0 w-6 border-t-2 border-dashed border-series-2" />Potential collaboration</span>
          </fieldset>
        )}
      </div>

      {view === "graph" ? (
        graph.isLoading ? <LoadingBlock rows={4} /> : graph.isError || !g ? <ErrorState error={graph.error} onRetry={() => graph.refetch()} /> :
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
          <Card className="h-[620px] overflow-hidden">
            <ReactFlow nodes={flow.nodes} edges={flow.edges} fitView fitViewOptions={{ padding: 0.04 }} minZoom={0.2} maxZoom={2} nodesConnectable={false}
              onNodeClick={(_, n) => setSelected({ kind: "node", node: g.nodes.find((x) => x.id === n.id)! })}
              onEdgeClick={(_, e) => setSelected({ kind: "edge", edge: g.edges.find((x) => x.id === e.id)! })}>
              <Background gap={24} color="#e2e8f0" />
              <Controls showInteractive={false} />
            </ReactFlow>
          </Card>
          <Card className="max-h-[620px] overflow-y-auto">
            <CardHeader title="Inspector" subtitle="Click a node or a connection to see why it is there." />
            <CardBody className="space-y-4">
              {!selected && <p className="text-[13px] text-ink-3">Nothing selected. Dashed orange lines are potential connections suggested from documented claims, not verified business relationships.</p>}
              {selected?.kind === "edge" && (
                <div className="space-y-2">
                  <Badge tone={selected.edge.kind === "potential_collaboration" ? "amber" : "neutral"}>{selected.edge.kind.replace(/_/g, " ")}</Badge>
                  <p className="text-[13.5px] text-ink-2">{selected.edge.explanation}</p>
                  {selected.edge.disclaimer && <p className="text-[12px] text-ink-3">{selected.edge.disclaimer}</p>}
                </div>
              )}
              {selected?.kind === "node" && !selectedPartner && (
                <div className="space-y-1.5">
                  <Badge tone="neutral">{TYPE_STYLE[selected.node.type].label}</Badge>
                  <p className="text-[14px] font-medium text-ink">{selected.node.label}</p>
                  {Object.entries(selected.node.data).filter(([k]) => !["focus", "company_id", "opportunity_id"].includes(k)).map(([k, v]) => (
                    <p key={k} className="text-[12.5px] text-ink-2"><span className="text-ink-3">{k.replace(/_/g, " ")}: </span>{Array.isArray(v) ? v.join("; ") : String(v)}</p>
                  ))}
                </div>
              )}
              {selectedPartner && <PartnerDetail c={selectedPartner} />}
            </CardBody>
          </Card>
        </div>
      ) : (
        items.length === 0
          ? <EmptyState title="No potential partners found yet" description="Suggestions appear when a documented need on one side meets a documented capability on the other." />
          : <ol className="space-y-4" aria-label="Recommended partners">{items.map((c) => <li key={c.id}><Card><CardBody><PartnerDetail c={c} /></CardBody></Card></li>)}</ol>
      )}
    </div>
  );
}

/** "Your X ↔ their Y" pairs from the documented need/offer rules (deduplicated, strongest first as returned by the API). */
function matchPairs(c: Collab): { key: string; yours: string; theirs: string; theyProvide: boolean }[] {
  const seen = new Set<string>();
  return c.rules.flatMap((r) => {
    const theyProvide = r.provider_id === c.partner_id;
    const yours = theyProvide ? r.need.label : r.offer.label;
    const theirs = theyProvide ? r.offer.label : r.need.label;
    const key = `${theyProvide}|${yours}|${theirs}`;
    if (seen.has(key)) return [];
    seen.add(key);
    return [{ key, yours, theirs, theyProvide }];
  }).slice(0, 3);
}

function PartnerDetail({ c }: { c: Collab }) {
  const claims = c.rules.slice(0, 3).flatMap((r) => [...r.need.claims, ...r.offer.claims]).filter((x, i, arr) => arr.findIndex((y) => y.id === x.id) === i);
  const inferredCount = claims.filter((x) => x.claim_type === "inferred").length;
  const pairs = matchPairs(c);
  const offers = c.complementary_capabilities.partner_offers;
  return (
    <div className="space-y-4">
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-[16px] font-semibold text-ink">{c.partner.name}</h3>
          <Badge tone={c.strength === "strong" ? "brand" : c.strength === "moderate" ? "teal" : "neutral"} title="Heuristic complementarity score — not a probability">{c.strength} · {Math.round(c.score)}</Badge>
          <Badge tone="amber">Potential — not a partnership</Badge>
          {inferredCount > 0 && <Badge tone="amber" title="At least one supporting claim is a rule-based inference, not a verified fact">{inferredCount === claims.length ? "Inferred match" : "Partly inferred"}</Badge>}
          <Badge tone={c.location?.scopes.includes("blekinge") ? "brand" : "neutral"} icon={<MapPin className="size-3" />}>{c.location?.label ?? "Location unknown"}</Badge>
        </div>
        {c.partner.description && <p className="mt-1.5 line-clamp-2 text-[13px] text-ink-2">{c.partner.description}</p>}
      </div>

      <dl className="grid gap-3 text-[13px] sm:grid-cols-2">
        <div className="rounded-lg bg-canvas p-3">
          <dt className="font-semibold text-ink">What they offer</dt>
          <dd className="mt-0.5 text-ink-2">{offers.join(", ") || "Not documented"}</dd>
        </div>
        <div className="rounded-lg bg-canvas p-3">
          <dt className="font-semibold text-ink">Why it is relevant</dt>
          <dd className="mt-0.5 text-ink-2">
            {pairs.length === 0 ? (c.why[0] ?? "Not documented") : (
              <ul className="space-y-0.5">{pairs.map((p) => <li key={p.key}>{p.theyProvide ? <>Your <span className="font-medium text-ink">{p.yours}</span> ↔ their <span className="font-medium text-ink">{p.theirs}</span></> : <>Their <span className="font-medium text-ink">{p.theirs}</span> ↔ your <span className="font-medium text-ink">{p.yours}</span></>}</li>)}</ul>
            )}
          </dd>
        </div>
        <div className="rounded-lg bg-canvas p-3 sm:col-span-2">
          <dt className="font-semibold text-ink">Potential mutual benefit</dt>
          <dd className="mt-0.5 text-ink-2">For you: {c.mutual_benefit.for_company}<br />For {c.partner.name}: {c.mutual_benefit.for_partner}</dd>
        </div>
      </dl>
      <div className="rounded-lg border border-brand-100 bg-brand-50/60 p-3 text-[13px]"><span className="font-semibold">Suggested first step: </span>{c.first_step}</div>
      <Uncertainty items={[...c.missing_information, ...c.uncertainties]} />

      <details className="group rounded-lg border border-line">
        <summary className="cursor-pointer select-none px-3 py-2 text-[13px] font-medium text-brand hover:underline">Evidence, scenario and score details</summary>
        <div className="space-y-4 border-t border-line p-3">
          <Section title="Why they may work well together"><ul className="list-disc space-y-1 pl-5 text-[13px] text-ink-2">{c.why.map((w) => <li key={w}>{w}</li>)}</ul></Section>
          {c.complementary_capabilities.company_offers.length > 0 && <div className="rounded-lg bg-canvas p-3 text-[12.5px]"><div className="font-medium text-ink">You offer them</div><div className="text-ink-2">{c.complementary_capabilities.company_offers.join(", ")}</div></div>}
          <Section title="Possible scenario"><p className="text-[13px] text-ink-2">{c.scenario}</p></Section>
          <Section title="Supporting evidence (documented claims)">
            <ul className="space-y-1.5">
              {claims.map((x) => (
                <li key={x.id} className="flex flex-wrap items-center gap-1.5 text-[12.5px]"><span className="text-ink">{x.label}</span><ClaimTypeBadge type={x.claim_type} /></li>
              ))}
            </ul>
          </Section>
          <Section title="Score criteria"><CriteriaBreakdown criteria={c.criteria} /></Section>
          {c.shared_opportunities.length > 0 && <Section title="Opportunities relevant to both"><ul className="space-y-1 text-[13px]">{c.shared_opportunities.map((o) => <li key={o.id} className="text-ink-2">{o.title} <span className="text-ink-3">({o.company_score} / {o.partner_score}{o.requires_consortium ? ", multi-party call" : ""})</span></li>)}</ul></Section>}
        </div>
      </details>
    </div>
  );
}
