import { FileSearch, HelpCircle, Info } from "lucide-react";
import type { ReactNode } from "react";
import { LoadingBlock } from "@/components/ui/primitives";
import { ClaimTypeBadge, ProvenanceBadge, SourceLink, VerificationBadge } from "@/components/shared/badges";
import { useEvidence } from "@/services/queries";
import type { Criterion, Evidence } from "@/types/api";
import { cn, formatDate } from "@/lib/utils";

interface CriterionLike { criterion?: string; label?: string; key?: string; value: number; max: number; explanation: string }

/** Horizontal contribution bars — one per criterion, labelled with value and explanation (never color alone). */
export function CriteriaBreakdown({ criteria, penalties, note }: { criteria: CriterionLike[]; penalties?: { key: string; value: number; explanation: string }[]; note?: string }) {
  return (
    <div className="space-y-2.5">
      <ul className="space-y-2.5" aria-label="Score criteria">
        {criteria.map((c, i) => {
          const name = c.label ?? c.criterion ?? c.key ?? `Criterion ${i + 1}`;
          const negative = c.value < 0;
          const pct = c.max > 0 ? Math.max(0, Math.min(100, (c.value / c.max) * 100)) : 0;
          return (
            <li key={name + i}>
              <div className="flex items-baseline justify-between gap-3 text-[13px]">
                <span className="font-medium text-ink">{name}</span>
                <span className="font-mono text-[12px] tabular-nums text-ink-2">{negative ? c.value.toFixed(1) : `${c.value.toFixed(1)} / ${c.max}`}</span>
              </div>
              {!negative && c.max > 0 && (
                <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-slate-100" aria-hidden>
                  <div className="h-full rounded-full bg-series-1" style={{ width: `${pct}%` }} />
                </div>
              )}
              <p className="mt-1 text-[12.5px] leading-snug text-ink-3">{c.explanation}</p>
            </li>
          );
        })}
      </ul>
      {penalties && penalties.length > 0 && (
        <ul className="space-y-1.5 rounded-lg border border-amber-200 bg-amber-50/60 p-3" aria-label="Penalties">
          {penalties.map((p) => (
            <li key={p.key} className="flex justify-between gap-3 text-[12.5px]">
              <span className="text-ink-2">{p.explanation}</span>
              <span className="font-mono tabular-nums text-ink">{p.value}</span>
            </li>
          ))}
        </ul>
      )}
      {note && <p className="flex items-start gap-1.5 text-[12px] text-ink-3"><Info className="mt-0.5 size-3.5 shrink-0" />{note}</p>}
    </div>
  );
}

export function MatchedConcepts({ criteria }: { criteria: Criterion[] }) {
  const rows = criteria.flatMap((c) => c.matches.map((m) => ({ ...m, criterion: c.label })));
  if (!rows.length) return <p className="text-[13px] text-ink-3">No concept of this opportunity matches the company profile.</p>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-[13px]">
        <thead className="text-[12px] text-ink-3">
          <tr><th className="py-1.5 pr-3 font-medium">Concept</th><th className="py-1.5 pr-3 font-medium">In opportunity</th><th className="py-1.5 font-medium">Supporting company claims</th></tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.map((r, i) => (
            <tr key={r.concept + i} className="align-top">
              <td className="py-2 pr-3 font-medium text-ink">{r.label}<div className="text-[11.5px] font-normal text-ink-3">{r.criterion}</div></td>
              <td className="py-2 pr-3 text-ink-2">{r.opportunity_terms.join(", ")}</td>
              <td className="py-2">
                <ul className="space-y-1">
                  {r.company_claims.map((c) => <li key={c.id} className="flex flex-wrap items-center gap-1.5"><span className="text-ink-2">{c.label}</span><ClaimTypeBadge type={c.claim_type} /></li>)}
                </ul>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function EvidenceItem({ ev }: { ev: Evidence }) {
  return (
    <li className="rounded-xl border border-line bg-white p-3.5">
      <div className="flex flex-wrap items-center gap-1.5">
        <ProvenanceBadge provenance={ev.provenance} />
        {ev.excerpt && <VerificationBadge status={ev.verification_status} />}
        <span className="text-[12px] text-ink-3">{ev.evidence_type.replace(/_/g, " ")}</span>
      </div>
      <p className="mt-2 text-[13.5px] font-medium text-ink">{ev.title}</p>
      <p className="text-[12px] text-ink-3">{ev.publisher} · retrieved {formatDate(ev.retrieved_at)}</p>
      {ev.excerpt ? (
        <blockquote className="mt-2 border-l-2 border-teal pl-3 text-[13px] italic leading-relaxed text-ink-2">“{ev.excerpt}”</blockquote>
      ) : (
        <p className="mt-2 text-[12.5px] text-ink-3">No excerpt stored ({ev.reuse_note || "metadata only"}).</p>
      )}
      <div className="mt-2 text-[13px]"><SourceLink href={ev.url}>Open original source</SourceLink></div>
    </li>
  );
}

export function EvidencePanel({ ids, evidence, title = "Evidence" }: { ids?: number[]; evidence?: Evidence[]; title?: string }) {
  const unique = Array.from(new Set((ids ?? []).filter(Boolean)));
  const q = useEvidence(evidence ? [] : unique);
  const items = evidence ?? q.data ?? [];
  return (
    <section aria-label={title}>
      <h4 className="mb-2 flex items-center gap-1.5 text-[13px] font-semibold text-ink"><FileSearch className="size-4 text-teal" />{title}</h4>
      {q.isLoading && !evidence ? <LoadingBlock rows={1} label="Loading evidence" /> :
        items.length ? <ul className="space-y-2">{items.map((e) => <EvidenceItem key={e.id} ev={e} />)}</ul> :
          <p className="text-[13px] text-ink-3">No direct source record for this item — it is derived from the matching rules listed above.</p>}
    </section>
  );
}

export function Uncertainty({ items }: { items: string[] }) {
  if (!items?.length) return null;
  return (
    <section aria-label="Uncertainty and missing information" className="rounded-xl border border-amber-200 bg-amber-50/50 p-3.5">
      <h4 className="mb-1.5 flex items-center gap-1.5 text-[13px] font-semibold text-ink"><HelpCircle className="size-4 text-amber-700" />Uncertain or missing</h4>
      <ul className="list-disc space-y-1 pl-5 text-[12.5px] text-ink-2">{Array.from(new Set(items)).map((u) => <li key={u}>{u}</li>)}</ul>
    </section>
  );
}

export function Section({ title, children, className, icon }: { title: string; children: ReactNode; className?: string; icon?: ReactNode }) {
  return (
    <section className={cn("space-y-2", className)}>
      <h4 className="flex items-center gap-1.5 text-[13px] font-semibold uppercase tracking-wide text-ink-3">{icon}{title}</h4>
      {children}
    </section>
  );
}
