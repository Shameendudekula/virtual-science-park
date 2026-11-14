import { Building2, CalendarDays, CalendarRange, ExternalLink, Filter, Landmark, LayoutGrid, Map as MapIcon, Search, Users } from "lucide-react";
import { Fragment, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useWorkspace } from "@/app/workspace";
import { Badge, Card, CardBody, CardHeader, EmptyState, ErrorState, LoadingBlock, PageHeader, Tabs, inputClass } from "@/components/ui/primitives";
import { BandBadge, DeadlineBadge, LocationBadges, ProvenanceBadge, SourceLink } from "@/components/shared/badges";
import { RegionalMap, type RegionalItem } from "@/components/charts/RegionalMap";
import { OpportunityCard, OpportunityDrawer } from "@/features/opportunity";
import { useCollaborations, useFunding, useOpportunities } from "@/services/queries";
import type { Opportunity } from "@/types/api";
import { deadlineGroup, formatDate, parseDate, sortByDeadline, titleCase, type DeadlineGroup } from "@/lib/utils";

const CATEGORY_OPTIONS = [
  ["", "All categories"], ["funding_call", "Funding calls"], ["innovation_programme", "Innovation programmes"], ["research_funding", "Research funding"],
  ["research_collaboration", "Research collaboration"], ["testing_facility", "Testing & test environments"], ["business_programme", "Business programmes"],
  ["event", "Events"], ["ecosystem_news", "Ecosystem news"],
] as const;
const REGIONS = [["", "All regions"], ["karlskrona", "Karlskrona"], ["blekinge", "Blekinge"], ["sweden", "Sweden"], ["europe", "Europe"], ["international", "International"], ["online", "Online"]] as const;
type View = "cards" | "map" | "timeline" | "funding" | "events";

const CRITERIA_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6"];

export default function Opportunities() {
  const { companyId } = useWorkspace();
  const [sp, setSp] = useSearchParams();
  const [view, setView] = useState<View>((sp.get("view") as View) || "cards");
  const [openId, setOpenId] = useState<number | null>(null);
  const params = useMemo(() => {
    const p = new URLSearchParams();
    ["category", "region", "technology", "source", "q"].forEach((k) => sp.get(k) && p.set(k, sp.get(k)!));
    p.set("min_score", sp.get("min_score") ?? "20");
    if (sp.get("include_closed") === "1") p.set("include_closed", "true");
    if (sp.get("category") === "ecosystem_news" || sp.get("include_news") === "1") p.set("include_news", "true");
    p.set("page_size", "100");
    return p;
  }, [sp]);
  const q = useOpportunities(companyId, params);
  const set = (k: string, v: string) => {
    const n = new URLSearchParams(sp);
    if (v) n.set(k, v); else n.delete(k);
    setSp(n, { replace: true });
  };

  return (
    <div className="space-y-5">
      <PageHeader eyebrow="Stage 2 · Find business opportunities" title="Opportunity Radar"
        description="Funding, programmes, test environments and events from collected public sources, ranked for your company with every criterion shown. VSP never decides eligibility." />

      <Card className="p-4">
        <div className="flex items-center gap-2 pb-3 text-[13px] font-semibold text-ink"><Filter className="size-4 text-brand" />Filters</div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
          <label className="relative lg:col-span-2">
            <span className="sr-only">Search opportunities</span>
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-ink-3" />
            <input className={`${inputClass} pl-9`} placeholder="Search title or programme" defaultValue={sp.get("q") ?? ""} onKeyDown={(e) => e.key === "Enter" && set("q", (e.target as HTMLInputElement).value)} onBlur={(e) => set("q", e.target.value)} />
          </label>
          <Select label="Category" value={sp.get("category") ?? ""} onChange={(v) => set("category", v)} options={CATEGORY_OPTIONS} />
          <Select label="Region" value={sp.get("region") ?? ""} onChange={(v) => set("region", v)} options={REGIONS} />
          <Select label="Technology area" value={sp.get("technology") ?? ""} onChange={(v) => set("technology", v)}
            options={[["", "All technologies"], ...((q.data?.facets.technologies ?? []).map((t) => [t, titleCase(t)] as const))]} />
          <Select label="Minimum relevance" value={sp.get("min_score") ?? "20"} onChange={(v) => set("min_score", v)}
            options={[["0", "Show all"], ["20", "Relevance ≥ 20"], ["35", "Relevant (≥ 35)"], ["55", "Strong (≥ 55)"]]} />
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-4 text-[13px] text-ink-2">
          <Select label="Source" inline value={sp.get("source") ?? ""} onChange={(v) => set("source", v)}
            options={[["", "All sources"], ...((q.data?.facets.sources ?? []).map((s) => [s, s.replace("bsp_", "Blue Science Park ").replace("vinnova", "Vinnova")] as const))]} />
          <label className="inline-flex items-center gap-2"><input type="checkbox" checked={sp.get("include_closed") === "1"} onChange={(e) => set("include_closed", e.target.checked ? "1" : "")} className="size-4 accent-[var(--color-brand)]" />Include closed</label>
          <label className="inline-flex items-center gap-2"><input type="checkbox" checked={sp.get("include_news") === "1"} onChange={(e) => set("include_news", e.target.checked ? "1" : "")} className="size-4 accent-[var(--color-brand)]" />Include ecosystem news</label>
        </div>
      </Card>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <Tabs label="View" value={view} onChange={(v) => { setView(v); set("view", v === "cards" ? "" : v); }}
          items={[{ value: "cards", label: <span className="inline-flex items-center gap-1.5"><LayoutGrid className="size-3.5" />Cards</span>, count: q.data?.total },
                  { value: "map", label: <span className="inline-flex items-center gap-1.5"><MapIcon className="size-3.5" />Regional map</span> },
                  { value: "timeline", label: <span className="inline-flex items-center gap-1.5"><CalendarRange className="size-3.5" />Deadline timeline</span> },
                  { value: "funding", label: <span className="inline-flex items-center gap-1.5"><Landmark className="size-3.5" />Unified funding</span> },
                  { value: "events", label: <span className="inline-flex items-center gap-1.5"><CalendarDays className="size-3.5" />Events</span> }]} />
        {q.isFetching && !q.isLoading && <span className="text-[12px] text-ink-3">Updating…</span>}
      </div>

      {view === "funding" ? <FundingView companyId={companyId} onOpen={setOpenId} /> :
        view === "events" ? <EventsView companyId={companyId} search={sp.get("q") ?? ""} region={sp.get("region") ?? ""} onOpen={setOpenId} /> :
        q.isLoading ? <LoadingBlock rows={4} /> : q.isError ? <ErrorState error={q.error} onRetry={() => q.refetch()} /> :
          q.data!.items.length === 0 ? <EmptyState title="No opportunities match these filters" description="Lower the minimum relevance or clear filters. Closed calls and news are hidden by default." /> :
            view === "cards" ? <CardsView items={q.data!.items} onOpen={setOpenId} /> :
              view === "map" ? <MapView items={q.data!.items} onOpen={setOpenId} companyId={companyId} /> :
                <TimelineView items={q.data!.items} onOpen={setOpenId} />}
      <OpportunityDrawer id={openId} companyId={companyId} onClose={() => setOpenId(null)} />
    </div>
  );
}

function Select({ label, value, onChange, options, inline }: { label: string; value: string; onChange: (v: string) => void; options: readonly (readonly [string, string])[]; inline?: boolean }) {
  return (
    <label className={inline ? "inline-flex items-center gap-2" : "block"}>
      <span className={inline ? "text-ink-3" : "sr-only"}>{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)} className={inline ? "h-8 rounded-md border border-line-2 bg-white px-2 text-[13px]" : inputClass} aria-label={label}>
        {options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
      </select>
    </label>
  );
}

function CardsView({ items, onOpen }: { items: Opportunity[]; onOpen: (id: number) => void }) {
  const top = items.filter((o) => o.match).slice(0, 8);
  const data = top.map((o) => {
    const row: Record<string, string | number> = { name: o.title.length > 38 ? `${o.title.slice(0, 36)}…` : o.title };
    o.match!.criteria.forEach((c) => (row[c.label] = Math.max(0, Math.round(c.value * 10) / 10)));
    return row;
  });
  const criteria = top[0]?.match?.criteria.map((c) => c.label) ?? [];
  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{items.map((o) => <div key={o.id} className="relative"><OpportunityCard opp={o} onOpen={() => onOpen(o.id)} /></div>)}</div>
      {data.length > 1 && (
        <Card>
          <CardHeader title="What drives the ranking" subtitle="Contribution of each criterion to the top results (before penalties). Hover for values." />
          <CardBody>
            <div className="h-[340px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data} layout="vertical" margin={{ left: 8, right: 16 }} barCategoryGap={8}>
                  <CartesianGrid horizontal={false} stroke="#eef2f7" />
                  <XAxis type="number" tick={{ fontSize: 12, fill: "#5b6b82" }} axisLine={false} tickLine={false} />
                  <YAxis type="category" dataKey="name" width={230} tick={{ fontSize: 12, fill: "#334155" }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={{ borderRadius: 10, border: "1px solid #e2e8f0", fontSize: 12 }} cursor={{ fill: "#f1f5f9" }} />
                  <Legend wrapperStyle={{ fontSize: 12, color: "#334155" }} iconType="circle" />
                  {criteria.map((c, i) => <Bar key={c} dataKey={c} stackId="s" fill={CRITERIA_COLORS[i % CRITERIA_COLORS.length]} stroke="#fff" strokeWidth={2} radius={i === criteria.length - 1 ? [0, 4, 4, 0] : 0} />)}
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardBody>
        </Card>
      )}
    </div>
  );
}

function MapView({ items, onOpen, companyId }: { items: Opportunity[]; onOpen: (id: number) => void; companyId: number }) {
  const collabs = useCollaborations(companyId);
  const mapItems: RegionalItem[] = [
    ...items.slice(0, 24).map((o) => ({
      id: `o${o.id}`, label: o.title, score: o.match?.relevance_score ?? 0, scopes: o.geo_scopes, inferred: o.geo_inferred,
      kind: (["event", "testing_facility", "business_programme", "ecosystem_news"].includes(o.category) ? "event" : "opportunity") as RegionalItem["kind"],
      onSelect: () => onOpen(o.id),
    })),
    ...(collabs.data?.items ?? []).filter((c) => c.score >= 25).map((c) => ({
      id: `p${c.partner_id}`, label: `${c.partner.name} (potential partner)`, score: Math.round(c.score), kind: "partner" as const,
      scopes: c.location?.scopes ?? [], inferred: !c.location?.verified,
    })),
  ];
  return (
    <Card>
      <CardHeader icon={<MapIcon className="size-4" />} title="Regional opportunity map"
        subtitle="Distance from home by geographic scope — a schematic, not a geographic map. Online items are never penalised for location." />
      <CardBody><RegionalMap items={mapItems} homeLabel="You" /></CardBody>
    </Card>
  );
}

function TimelineView({ items, onOpen }: { items: Opportunity[]; onOpen: (id: number) => void }) {
  const dated = items.filter((o) => o.deadline_at).sort((a, b) => a.deadline_at!.localeCompare(b.deadline_at!));
  const undated = items.filter((o) => !o.deadline_at);
  const months = new Map<string, Opportunity[]>();
  dated.forEach((o) => {
    const k = new Date(o.deadline_at!).toLocaleDateString("en-GB", { month: "long", year: "numeric", timeZone: "Europe/Stockholm" });
    months.set(k, [...(months.get(k) ?? []), o]);
  });
  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
      <Card>
        <CardHeader icon={<CalendarRange className="size-4" />} title="Deadline timeline" subtitle="Only deadlines stated in the source are plotted. Placeholder dates are rejected." />
        <CardBody>
          {dated.length === 0 ? <p className="text-[13px] text-ink-3">No stated deadlines for these filters.</p> : (
            <ol className="relative space-y-6 border-l-2 border-line pl-6">
              {[...months.entries()].map(([month, list]) => (
                <li key={month}>
                  <span className="absolute -left-[7px] mt-1 size-3 rounded-full border-2 border-white bg-series-1" aria-hidden />
                  <h3 className="text-[13px] font-semibold uppercase tracking-wide text-ink-3">{month}</h3>
                  <ul className="mt-2 space-y-2">
                    {list.map((o) => (
                      <li key={o.id}>
                        <button onClick={() => onOpen(o.id)} className="w-full rounded-xl border border-line p-3 text-left hover:border-brand-100 hover:bg-brand-50/40">
                          <div className="flex flex-wrap items-center gap-1.5">
                            <span className="font-mono text-[12px] text-ink-2">{formatDate(o.deadline_at)}</span>
                            {o.match && <BandBadge band={o.match.relevance_band} score={o.match.relevance_score} />}
                            <DeadlineBadge deadline={o.deadline_at} days={o.timeliness.days_left} />
                          </div>
                          <div className="mt-1 text-[14px] font-medium text-ink">{o.title}</div>
                        </button>
                      </li>
                    ))}
                  </ul>
                </li>
              ))}
            </ol>
          )}
        </CardBody>
      </Card>
      <Card>
        <CardHeader title="No deadline stated" subtitle={`${undated.length} items`} />
        <CardBody>
          <ul className="space-y-2 text-[13px]">
            {undated.slice(0, 15).map((o) => <li key={o.id}><button onClick={() => onOpen(o.id)} className="text-left text-ink hover:text-brand">{o.title}</button><div className="text-[12px] text-ink-3">{o.category_label} · {o.timeliness.label}</div></li>)}
          </ul>
        </CardBody>
      </Card>
    </div>
  );
}

/**
 * Event discovery limited to what the collected data supports. The collected event records contain only a title,
 * the source's listing (publication) date and the official link, so event dates, venues, organisers, sponsors,
 * exhibitors, speakers and logos are stated as unavailable rather than guessed.
 */
function EventsView({ companyId, search, region, onOpen }: { companyId: number; search: string; region: string; onOpen: (id: number) => void }) {
  const params = useMemo(() => {
    const p = new URLSearchParams({ category: "event", min_score: "0", include_closed: "true", page_size: "100" });
    if (search) p.set("q", search);
    if (region) p.set("region", region);
    return p;
  }, [search, region]);
  const q = useOpportunities(companyId, params);
  // Newest listing first (event dates are not collected); copied, never mutating the cached response.
  const sorted = useMemo(() => [...(q.data?.items ?? [])].sort((a, b) => (parseDate(b.published_at)?.getTime() ?? 0) - (parseDate(a.published_at)?.getTime() ?? 0)), [q.data]);
  if (q.isLoading) return <LoadingBlock rows={3} />;
  if (q.isError) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  if (sorted.length === 0) return <EmptyState title="No events in the collected data" description="Clear the search or region filter to see all collected event listings." />;
  const groups: [string, Opportunity[]][] = [
    ["Listed in the last 4 months", sorted.filter((o) => o.timeliness.recent)],
    ["Older listings — may have passed", sorted.filter((o) => !o.timeliness.recent)],
  ];
  return (
    <div className="space-y-5">
      <div className="flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50/60 px-4 py-3 text-[13px] text-ink-2">
        <CalendarDays className="mt-0.5 size-4 shrink-0 text-amber-700" aria-hidden />
        <span>Event dates, organisers and sponsors are not in the collected event data, so no event is shown as upcoming. Listings are sorted by the date the source published them. Open the official page for current details.</span>
      </div>
      {groups.map(([heading, list]) => list.length > 0 && (
        <section key={heading} aria-label={heading}>
          <h2 className="mb-2 text-[12px] font-semibold uppercase tracking-wide text-ink-3">{heading} <span className="font-normal">({list.length})</span></h2>
          <ul className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{list.map((o) => <li key={o.id}><EventCard o={o} onOpen={() => onOpen(o.id)} /></li>)}</ul>
        </section>
      ))}
    </div>
  );
}

function EventCard({ o, onOpen }: { o: Opportunity; onOpen: () => void }) {
  return (
    <Card className="flex h-full flex-col p-4">
      <div className="flex flex-wrap items-center gap-1.5">
        <LocationBadges scopes={o.geo_scopes} inferred={o.geo_inferred} />
        {o.event_format === "online" && <Badge tone="teal">Online</Badge>}
        {o.match && <BandBadge band={o.match.relevance_band} score={o.match.relevance_score} />}
      </div>
      <h3 className="mt-2.5 text-[15px] font-semibold leading-snug text-ink"><button onClick={onOpen} className="text-left hover:text-brand">{o.title}</button></h3>
      <dl className="mt-2.5 space-y-1.5 text-[12.5px]">
        <div className="flex items-start gap-1.5">
          <dt><CalendarDays className="mt-0.5 size-3.5 text-ink-3" aria-label="Date" /></dt>
          <dd className="text-ink-2"><span className="font-medium text-ink">Event date not in collected data</span><br /><span className="text-ink-3">Listing published {formatDate(o.published_at)}</span></dd>
        </div>
        <div className="flex items-start gap-1.5">
          <dt><Building2 className="mt-0.5 size-3.5 text-ink-3" aria-label="Organiser" /></dt>
          <dd className="text-ink-2">Listed by {o.organisation} · organiser not in collected data</dd>
        </div>
        <div className="flex items-start gap-1.5">
          <dt><Users className="mt-0.5 size-3.5 text-ink-3" aria-label="Sponsors and participants" /></dt>
          <dd className="text-ink-3">Sponsor information not available in the collected event data.</dd>
        </div>
      </dl>
      <div className="mt-auto flex flex-wrap items-center justify-between gap-2 pt-3">
        <ProvenanceBadge provenance={o.provenance} />
        <SourceLink href={o.source_url}>Official event page</SourceLink>
      </div>
    </Card>
  );
}

function FundingView({ companyId, onOpen }: { companyId: number; onOpen: (id: number) => void }) {
  const q = useFunding(companyId);
  // Sorted copy; the cached API response is never mutated.
  const sorted = useMemo(() => sortByDeadline(q.data?.items ?? []), [q.data]);
  if (q.isLoading) return <LoadingBlock rows={3} />;
  if (q.isError) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  const f = q.data!;
  const GROUP_HEADING: Record<DeadlineGroup, string> = { upcoming: "Open — nearest deadline first", closed: "Closed", undated: "No deadline stated in source" };
  return (
    <div className="space-y-5">
      <div className="grid gap-4 md:grid-cols-3">
        {f.sources.map((s) => (
          <Card key={s.key} className="p-4">
            <div className="flex items-center justify-between gap-2">
              <span className="text-[14px] font-semibold text-ink">{s.name.split("—")[0]}</span>
              <Badge tone={s.integrated ? "green" : "neutral"}>{s.integrated ? "Integrated" : s.key === "ymner" ? "External link" : "Not activated"}</Badge>
            </div>
            <p className="mt-2 text-[12.5px] leading-relaxed text-ink-3">{s.integrated ? "Calls and application rounds are collected and ranked below." : s.reason}</p>
            {s.link && <div className="mt-3 text-[13px]"><SourceLink href={s.link}>{s.key === "ymner" ? "Search Ymner yourself" : "Open portal"}</SourceLink></div>}
          </Card>
        ))}
      </div>
      <Card>
        <CardHeader icon={<Landmark className="size-4" />} title="Funding by application deadline" subtitle={f.note} />
        <CardBody className="overflow-x-auto">
          <p className="mb-3 flex items-start gap-1.5 text-[12.5px] text-ink-3"><CalendarRange className="mt-0.5 size-3.5 shrink-0" aria-hidden />
            Sorted by application deadline (Europe/Stockholm time). Dates come from the collected snapshot; confirm on the source before applying.</p>
          <table className="w-full min-w-[720px] text-left text-[13px]">
            <thead className="text-[12px] text-ink-3"><tr><th className="pb-2 font-medium">Opportunity</th><th className="pb-2 font-semibold text-ink">Application deadline</th><th className="pb-2 font-medium">Relevance</th><th className="pb-2 font-medium">Area</th><th className="pb-2 font-medium">Source</th></tr></thead>
            <tbody className="divide-y divide-line">
              {sorted.map((i, idx) => {
                const group = deadlineGroup(i.deadline_at, i.timeliness.days_left);
                const newGroup = idx === 0 || group !== deadlineGroup(sorted[idx - 1].deadline_at, sorted[idx - 1].timeliness.days_left);
                return (
                  <Fragment key={i.id}>
                    {newGroup && <tr><th colSpan={5} scope="colgroup" className="bg-canvas px-2 py-1.5 text-[11.5px] font-semibold uppercase tracking-wide text-ink-3">{GROUP_HEADING[group]}</th></tr>}
                    <tr className="align-top">
                      <td className="py-2.5 pr-3"><button onClick={() => onOpen(i.id)} className="text-left font-medium text-ink hover:text-brand">{i.title}</button><div className="text-[12px] text-ink-3">{i.programme ?? i.organisation}</div></td>
                      <td className="py-2.5 pr-3"><DeadlineBadge deadline={i.deadline_at} days={i.timeliness.days_left} status={i.deadline_status} /></td>
                      <td className="py-2.5 pr-3"><BandBadge band={i.band} score={i.score} /></td>
                      <td className="py-2.5 pr-3"><LocationBadges scopes={i.geography.scopes} inferred={i.geography.inferred} /></td>
                      <td className="py-2.5"><div className="flex items-center gap-1.5"><ProvenanceBadge provenance={i.provenance} /><a href={i.url} target="_blank" rel="noopener noreferrer" aria-label={`Open source record: ${i.title} (opens in a new tab)`} className="text-brand"><ExternalLink className="size-3.5" aria-hidden /></a></div>
                        {i.also_listed_by.length > 0 && <div className="text-[11.5px] text-ink-3">Also listed by {i.also_listed_by.map((a) => a.source).join(", ")}</div>}</td>
                    </tr>
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </CardBody>
      </Card>
    </div>
  );
}
