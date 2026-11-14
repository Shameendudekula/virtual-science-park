import { CalendarClock, FileText, Lightbulb, Scale, Target, Users } from "lucide-react";
import { Badge, Card, Drawer, ErrorState, LoadingBlock } from "@/components/ui/primitives";
import { BandBadge, DeadlineBadge, LocationBadges, ProvenanceBadge, RegionalNote, SourceLink } from "@/components/shared/badges";
import { CriteriaBreakdown, EvidencePanel, MatchedConcepts, Section, Uncertainty } from "@/components/shared/explain";
import { useOpportunity } from "@/services/queries";
import type { Opportunity } from "@/types/api";
import { formatDate } from "@/lib/utils";

export function OpportunityCard({ opp, onOpen }: { opp: Opportunity; onOpen: () => void }) {
  const m = opp.match;
  return (
    <Card className="group relative flex h-full flex-col p-5 transition hover:-translate-y-0.5 hover:shadow-[var(--shadow-lift)]">
      <div className="flex flex-wrap items-center gap-1.5">
        <Badge tone="brand">{opp.category_label}</Badge>
        {m && <BandBadge band={m.relevance_band} score={m.relevance_score} />}
        <LocationBadges scopes={opp.geo_scopes} inferred={opp.geo_inferred} />
      </div>
      <button onClick={onOpen} className="mt-3 text-left text-[15px] font-semibold leading-snug text-ink after:absolute after:inset-0 group-hover:text-brand focus-visible:outline-none">
        <span className="line-clamp-2">{opp.title}</span>
      </button>
      <p className="mt-1 text-[12.5px] text-ink-3">{opp.organisation}{opp.programme ? ` · ${opp.programme}` : ""}</p>
      {m?.reasons[0] && <p className="mt-3 line-clamp-2 text-[13px] leading-relaxed text-ink-2"><span className="font-medium text-ink">Why: </span>{m.reasons[0]}</p>}
      <div className="mt-auto flex flex-wrap items-center gap-1.5 pt-4">
        {opp.deadline_at || !["event", "ecosystem_news", "business_programme", "testing_facility"].includes(opp.category)
          ? <DeadlineBadge deadline={opp.deadline_at} days={opp.timeliness.days_left} status={opp.deadline_status} />
          : <Badge tone="neutral">{opp.timeliness.label}</Badge>}
        <ProvenanceBadge provenance={opp.provenance} />
        {opp.event_format === "online" && <Badge tone="teal">Online</Badge>}
      </div>
    </Card>
  );
}

export function OpportunityDrawer({ id, companyId, onClose }: { id: number | null; companyId: number; onClose: () => void }) {
  const q = useOpportunity(id ?? undefined, companyId);
  const o = q.data;
  const m = o?.match;
  return (
    <Drawer open={id !== null} onClose={onClose} title={o?.title ?? "Opportunity"}>
      {q.isLoading && <LoadingBlock rows={4} />}
      {q.isError && <ErrorState error={q.error} onRetry={() => q.refetch()} />}
      {o && (
        <div className="space-y-6">
          <div className="flex flex-wrap gap-1.5">
            <Badge tone="brand">{o.category_label}</Badge>
            {m && <BandBadge band={m.relevance_band} score={m.relevance_score} />}
            <DeadlineBadge deadline={o.deadline_at} days={o.timeliness.days_left} status={o.deadline_status} />
            <ProvenanceBadge provenance={o.provenance} />
            <LocationBadges scopes={o.geo_scopes} inferred={o.geo_inferred} max={3} />
          </div>

          <dl className="grid grid-cols-1 gap-3 text-[13px] sm:grid-cols-2">
            <Meta label="Organisation" value={o.organisation} />
            <Meta label="Programme" value={o.programme ?? "Not stated in source"} />
            <Meta label="Opens" value={formatDate(o.opens_at)} />
            <Meta label="Deadline" value={o.deadline_status === "placeholder_rejected" ? "Not stated (placeholder date in source rejected)" : formatDate(o.deadline_at)} />
            <Meta label="Published" value={formatDate(o.published_at)} />
            <Meta label="Source" value={<>{o.source_name} · retrieved {formatDate(o.retrieved_at)}</>} />
          </dl>

          <div className="flex flex-wrap gap-4 text-[13.5px]">
            <SourceLink href={o.source_url}>Official source record</SourceLink>
            {o.apply_url && <SourceLink href={o.apply_url}>Application page</SourceLink>}
          </div>

          {(o.purpose_text || o.description) && (
            <Section title="From the source" icon={<FileText className="size-3.5" />}>
              <p className="text-[13.5px] leading-relaxed text-ink-2">{o.purpose_text ?? o.description}</p>
              {o.funding_text && <p className="text-[13px] text-ink-2"><span className="font-medium text-ink">Funding (source): </span>{o.funding_text}</p>}
              {o.title_original && <p className="text-[12px] text-ink-3">Original title: {o.title_original}</p>}
            </Section>
          )}
          {!o.purpose_text && !o.description && (
            <p className="rounded-lg bg-canvas p-3 text-[13px] text-ink-3">Only title-level metadata was collected for this item (content reuse not confirmed). Open the source to read details.</p>
          )}

          <Section title="Eligibility" icon={<Scale className="size-3.5" />}>
            {o.eligibility_text ? (
              <blockquote className="border-l-2 border-teal pl-3 text-[13px] italic text-ink-2">“{o.eligibility_text}”</blockquote>
            ) : null}
            <p className="text-[12.5px] text-ink-3">{m?.eligibility.note ?? (o.eligibility_text ? "Quoted from the source. VSP does not assess eligibility." : "Not stated in source.")}</p>
          </Section>

          {m && (
            <>
              <Section title="Why it matches" icon={<Target className="size-3.5" />}>
                <ul className="list-disc space-y-1 pl-5 text-[13.5px] text-ink-2">{m.reasons.map((r) => <li key={r}>{r}</li>)}</ul>
                <RegionalNote geo={m.geography} />
              </Section>
              <Section title="Matched concepts & supporting claims" icon={<Users className="size-3.5" />}>
                <MatchedConcepts criteria={m.criteria} />
              </Section>
              <Section title="Relevance criteria" icon={<CalendarClock className="size-3.5" />}>
                <CriteriaBreakdown criteria={m.criteria} penalties={m.penalties} note={m.score_note} />
                <div className="grid gap-2 sm:grid-cols-2">
                  <div className="rounded-lg bg-canvas p-3 text-[12.5px]"><div className="font-medium text-ink">Evidence quality</div><div className="text-ink-2">{m.evidence_quality.label}</div></div>
                  <div className="rounded-lg bg-canvas p-3 text-[12.5px]"><div className="font-medium text-ink">Information completeness</div><div className="text-ink-2">{m.completeness.score_pct}% · missing: {m.completeness.missing.join(", ") || "none"}</div></div>
                </div>
              </Section>
              <Section title="Business value & next action" icon={<Lightbulb className="size-3.5" />}>
                <p className="text-[13.5px] text-ink-2"><span className="font-medium text-ink">Potential value (generated explanation): </span>{m.business_value}</p>
                <p className="rounded-lg border border-brand-100 bg-brand-50/60 p-3 text-[13.5px] text-ink"><span className="font-semibold">Next: </span>{m.next_action}</p>
              </Section>
              <Uncertainty items={m.missing_information} />
            </>
          )}
          <EvidencePanel evidence={o.evidence ? [o.evidence] : []} title="Source evidence" />
        </div>
      )}
    </Drawer>
  );
}

function Meta({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <dt className="text-[12px] text-ink-3">{label}</dt>
      <dd className="font-medium text-ink">{value}</dd>
    </div>
  );
}
