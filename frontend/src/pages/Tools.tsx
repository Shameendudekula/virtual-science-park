import { Download, FileText, GitCompareArrows, History, Printer, Search as SearchIcon, Sparkles } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { useWorkspace } from "@/app/workspace";
import { Badge, Button, Card, CardBody, CardHeader, EmptyState, ErrorState, LoadingBlock, PageHeader, inputClass } from "@/components/ui/primitives";
import { ClaimTypeBadge, SourceLink, TierBadge } from "@/components/shared/badges";
import { CriteriaBreakdown, Section, Uncertainty } from "@/components/shared/explain";
import { OpportunityDrawer } from "@/features/opportunity";
import { api } from "@/lib/api";
import { useBrief, useCompanies, useCompare, useSearch, useSearchHistory } from "@/services/queries";
import { formatDate } from "@/lib/utils";

// ------------------------------------------------------------------------------------------- Compare
export function Compare() {
  const { companyId } = useWorkspace();
  const companies = useCompanies(true);
  const [b, setB] = useState<number | undefined>();
  const other = b ?? companies.data?.items.find((c) => c.id !== companyId && c.is_demo_company)?.id;
  const q = useCompare(companyId, other);
  const d = q.data;
  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Tool" title="Compare companies" description="Shared areas show similarity. Only the complementarity section reflects collaboration potential."
        actions={
          <label className="flex items-center gap-2 text-[13px] text-ink-2">Compare with
            <select value={other ?? ""} onChange={(e) => setB(Number(e.target.value))} className={`${inputClass} w-64`}>
              {companies.data?.items.filter((c) => c.id !== companyId).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </label>} />
      {q.isLoading && <LoadingBlock rows={3} />}
      {q.isError && <ErrorState error={q.error} onRetry={() => q.refetch()} />}
      {d && (
        <>
          <div className="grid gap-4 md:grid-cols-3">
            <ListCard title="Shared capabilities" items={d.shared_capabilities.map((x) => x.label)} />
            <ListCard title="Shared technologies" items={d.shared_technologies.map((x) => x.label)} />
            <ListCard title="Shared industries" items={d.shared_industries.map((x) => x.label)} />
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <ListCard title={`Only ${d.a.name}`} items={[...d.only_a_capabilities, ...d.only_a_technologies].map((x) => x.label)} />
            <ListCard title={`Only ${d.b.name}`} items={[...d.only_b_capabilities, ...d.only_b_technologies].map((x) => x.label)} />
          </div>
          <Card>
            <CardHeader icon={<GitCompareArrows className="size-4" />} title="Complementarity (potential collaboration)" subtitle={d.note} />
            <CardBody className="space-y-4">
              {d.complementarity ? (
                <>
                  <div className="flex flex-wrap gap-2"><Badge tone="brand">{d.complementarity.strength} · {Math.round(d.complementarity.score)}</Badge><Badge tone="amber">Potential — not a partnership</Badge></div>
                  <ul className="list-disc space-y-1 pl-5 text-[13.5px] text-ink-2">{d.complementarity.why.map((w) => <li key={w}>{w}</li>)}</ul>
                  <p className="text-[13.5px] text-ink-2"><span className="font-medium text-ink">Scenario: </span>{d.complementarity.scenario}</p>
                  <CriteriaBreakdown criteria={d.complementarity.criteria} />
                </>
              ) : <p className="text-[13.5px] text-ink-3">No complementarity rule fired between these two organisations.</p>}
              {d.joint_opportunities.length > 0 && (
                <Section title="Opportunities relevant to both">
                  <ul className="space-y-1 text-[13px]">{d.joint_opportunities.map((o) => <li key={o.id} className="text-ink-2">{o.title} <span className="text-ink-3">({o.a_score} / {o.b_score}{o.requires_consortium ? " · multi-party call" : ""})</span></li>)}</ul>
                </Section>
              )}
              <Uncertainty items={d.missing_information.map((m) => `${m.company}: not stated in collected sources — ${m.unknown_fields.join(", ")}`)} />
            </CardBody>
          </Card>
        </>
      )}
    </div>
  );
}

function ListCard({ title, items }: { title: string; items: string[] }) {
  return (
    <Card>
      <CardHeader title={title} subtitle={`${items.length}`} />
      <CardBody className="flex flex-wrap gap-1.5">{items.length ? items.map((i) => <Badge key={i} tone="neutral">{i}</Badge>) : <span className="text-[13px] text-ink-3">None</span>}</CardBody>
    </Card>
  );
}

// ------------------------------------------------------------------------------------------- Brief
export function Brief() {
  const { companyId, companyName } = useWorkspace();
  const q = useBrief(companyId);
  const [downloading, setDownloading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const downloadPdf = async () => {
    setDownloading(true);
    setErr(null);
    try {
      const blob = await api<Blob>(`/api/companies/${companyId}/innovation-brief?format=pdf`);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `innovation-brief-${companyName.toLowerCase().replace(/\W+/g, "-")}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setDownloading(false);
    }
  };
  if (q.isLoading) return <LoadingBlock rows={6} label="Generating brief" />;
  if (q.isError) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  const b = q.data!;
  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Tool" title="Innovation brief" description="A company-specific brief built only from application records and source evidence."
        actions={<><Button variant="outline" icon={<Printer className="size-4" />} onClick={() => window.print()} className="no-print">Print</Button><Button icon={<Download className="size-4" />} loading={downloading} onClick={downloadPdf} className="no-print">Export PDF</Button></>} />
      {err && <p role="alert" className="text-[13px] text-critical">{err}</p>}
      <Card className="mx-auto max-w-4xl">
        <CardBody className="space-y-7 p-8">
          <div>
            <div className="text-[12px] font-semibold uppercase tracking-wider text-brand">Virtual Science Park · Innovation brief</div>
            <h2 className="mt-1 text-[24px] font-semibold text-ink">{b.company.name}</h2>
            <p className="text-[12.5px] text-ink-3">Generated {formatDate(b.generated_at)} · {b.data_freshness} · membership {b.company.membership_status}</p>
          </div>
          <Section title="Executive summary" icon={<Sparkles className="size-3.5" />}>
            <p className="font-medium text-ink">{b.executive_summary.headline}</p>
            <ul className="list-disc space-y-1 pl-5 text-[14px] text-ink-2">{b.executive_summary.bullets.map((x) => <li key={x}>{x}</li>)}</ul>
          </Section>
          <Section title="Company profile">
            <ul className="space-y-1.5 text-[13.5px]">{b.profile.map((p, i) => <li key={i} className="text-ink-2"><span className="font-medium text-ink">{p.label}: </span>{p.value} <ClaimTypeBadge type={p.claim_type as "source_stated"} />{p.evidence_id && <sup className="ml-0.5 text-brand">[E{p.evidence_id}]</sup>}</li>)}</ul>
          </Section>
          <Section title="Most relevant opportunities">
            <ul className="space-y-2.5">{b.opportunities.map((o) => <li key={o.id} className="text-[13.5px]"><div className="font-medium text-ink">{o.title} <span className="text-ink-3">({o.organisation}) · {o.score} · deadline {o.deadline}</span>{o.evidence_id && <sup className="ml-0.5 text-brand">[E{o.evidence_id}]</sup>}</div><div className="text-ink-2">{o.why.join(" ")}</div><div className="text-[12px] text-ink-3">{o.eligibility}</div></li>)}</ul>
          </Section>
          <Section title="Emerging technology recommendations">
            <ul className="space-y-1.5 text-[13.5px]">{b.technologies.map((t) => <li key={t.name} className="text-ink-2"><span className="font-medium text-ink">{t.name}</span> ({t.ring}, {t.relation}) — {t.application ?? t.next_step}</li>)}</ul>
          </Section>
          <Section title="Potential collaboration partners">
            <ul className="space-y-2 text-[13.5px]">{b.partners.map((p) => <li key={p.name} className="text-ink-2"><span className="font-medium text-ink">{p.name}</span> ({p.strength}, potential): {p.why[0]} <span className="text-ink-3">First step: {p.first_step}</span></li>)}</ul>
          </Section>
          <Section title="Prioritised actions">
            <ol className="space-y-1.5 text-[13.5px]">{b.actions.map((a, i) => <li key={i} className="flex flex-wrap items-center gap-2 text-ink-2"><TierBadge tier={a.tier as "high"} />{a.title}</li>)}</ol>
          </Section>
          <Section title="Source references" icon={<FileText className="size-3.5" />}>
            <ul className="space-y-1 text-[12.5px]">{b.evidence.map((e) => <li key={e.id} className="text-ink-2">[E{e.id}] {e.publisher}: {e.title} — <SourceLink href={e.url}>{new URL(e.url).hostname}</SourceLink> <span className="text-ink-3">(retrieved {e.retrieved_at}, {e.provenance})</span></li>)}</ul>
          </Section>
          <Section title="Data limitations"><ul className="list-disc space-y-1 pl-5 text-[12.5px] text-ink-3">{b.limitations.map((l) => <li key={l}>{l}</li>)}</ul></Section>
        </CardBody>
      </Card>
    </div>
  );
}

// ------------------------------------------------------------------------------------------- Search
const EXAMPLES = [
  "Which funding opportunities are relevant to Ocean Harvesting?",
  "Which companies have complementary expertise in marine technology?",
  "What technologies could improve industrial energy systems?",
  "Which research opportunities should Cleura explore?",
];

export function SearchPage() {
  const { companyId } = useWorkspace();
  const [sp, setSp] = useSearchParams();
  const [text, setText] = useState(sp.get("q") ?? "");
  const query = sp.get("q") ?? "";
  const q = useSearch(query, companyId);
  const history = useSearchHistory(true);
  const [openOpp, setOpenOpp] = useState<number | null>(null);
  const refetchHistory = history.refetch;
  useEffect(() => {
    if (q.data) refetchHistory();
  }, [q.data, refetchHistory]);
  const submit = (e?: FormEvent, v?: string) => {
    e?.preventDefault();
    const value = (v ?? text).trim();
    if (value.length >= 2) {
      setText(value);
      setSp({ q: value });
    }
  };
  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Tool" title="Ask VSP" description="Questions are translated into structured searches over the VSP database. Answers are records with explanations — no generated text." />
      <form onSubmit={submit} className="flex gap-2" role="search">
        <label className="relative flex-1"><span className="sr-only">Question</span>
          <SearchIcon className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-ink-3" />
          <input value={text} onChange={(e) => setText(e.target.value)} className={`${inputClass} h-12 pl-9 text-[15px]`} placeholder="Ask about funding, partners or technologies" />
        </label>
        <Button type="submit" size="lg">Search</Button>
      </form>
      <div className="flex flex-wrap gap-2">{EXAMPLES.map((ex) => <button key={ex} onClick={() => submit(undefined, ex)} className="rounded-full border border-line-2 bg-white px-3 py-1.5 text-[12.5px] text-ink-2 hover:border-brand hover:text-brand">{ex}</button>)}</div>
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_300px]">
        <div className="space-y-4">
          {!query && <EmptyState title="Ask a question to start" description="Try one of the examples above." icon={<SearchIcon className="size-5" />} />}
          {q.isLoading && <LoadingBlock rows={3} label="Searching" />}
          {q.isError && <ErrorState error={q.error} onRetry={() => q.refetch()} />}
          {q.data && (
            <>
              <Card className="p-4 text-[13px]">
                <div className="font-semibold text-ink">Interpreted as</div>
                <div className="mt-1.5 flex flex-wrap gap-1.5">
                  <Badge tone="brand">intent: {q.data.query.intent}</Badge>
                  {q.data.query.company_name && <Badge tone="navy">company: {q.data.query.company_name}</Badge>}
                  {q.data.query.concepts.map((c) => <Badge key={c.key} tone="teal">{c.label}</Badge>)}
                  {q.data.query.categories.map((c) => <Badge key={c} tone="neutral">{c.replace(/_/g, " ")}</Badge>)}
                </div>
                {q.data.query.notes.map((n) => <p key={n} className="mt-1.5 text-ink-3">{n}</p>)}
                <p className="mt-1.5 text-[12px] text-ink-3">{q.data.note} Parser: {q.data.query.parser}.</p>
              </Card>
              {q.data.results.length === 0 ? <EmptyState title="No matching records" description="Try naming a technology, an industry or a company." /> : (
                <ul className="space-y-3">
                  {q.data.results.map((r) => (
                    <li key={`${r.type}-${r.id}-${r.company_id ?? ""}`}>
                      <Card className="p-4">
                        <div className="flex flex-wrap items-center gap-1.5"><Badge tone="neutral">{r.type}</Badge>{r.band && <Badge tone="brand">{r.band}</Badge>}<Badge tone="neutral">score {r.score}</Badge></div>
                        {r.type === "opportunity" ? <button onClick={() => setOpenOpp(Number(r.id))} className="mt-1.5 text-left text-[15px] font-semibold text-ink hover:text-brand">{r.title}</button> : <div className="mt-1.5 text-[15px] font-semibold text-ink">{r.title}</div>}
                        <div className="text-[12.5px] text-ink-3">{r.subtitle}</div>
                        <ul className="mt-2 list-disc space-y-0.5 pl-5 text-[13px] text-ink-2">{r.why.map((w) => <li key={w}>{w}</li>)}</ul>
                      </Card>
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </div>
        <Card>
          <CardHeader icon={<History className="size-4" />} title="Your recent questions" subtitle="Visible only in this company workspace." />
          <CardBody>
            {history.data?.length ? <ul className="space-y-1.5 text-[13px]">{history.data.map((h) => <li key={h.id}><button onClick={() => submit(undefined, h.query)} className="text-left text-ink hover:text-brand">{h.query}</button><div className="text-[11.5px] text-ink-3">{h.result_count} results · {formatDate(h.created_at)}</div></li>)}</ul>
              : <p className="text-[13px] text-ink-3">No questions yet.</p>}
          </CardBody>
        </Card>
      </div>
      <OpportunityDrawer id={openOpp} companyId={companyId} onClose={() => setOpenOpp(null)} />
    </div>
  );
}
