import { zodResolver } from "@hookform/resolvers/zod";
import { Check, ChevronDown, Clock, History, Lightbulb, MapPin, Pencil, Plus, RotateCcw, X } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { READ_ONLY_HINT, useReadOnly, useWorkspace } from "@/app/workspace";
import { Badge, Button, Card, CardBody, CardHeader, ErrorState, Field, LoadingBlock, PageHeader, inputClass } from "@/components/ui/primitives";
import { ClaimTypeBadge, SourceLink } from "@/components/shared/badges";
import { EvidenceItem } from "@/components/shared/explain";
import { RankingDiff } from "@/features/priorities";
import { usePatchProfile, useProfile, useReviewClaim } from "@/services/queries";
import type { Claim, RankingChange } from "@/types/api";
import { cn, formatDateTime, titleCase } from "@/lib/utils";

const FIELD_ORDER = ["overview", "product", "service", "technology", "capability", "industry", "research_interest", "business_focus", "interest", "project", "documented_collaboration", "location"];
const FIELD_LABEL: Record<string, string> = {
  overview: "Company overview", product: "Products", service: "Services", technology: "Core technologies", capability: "Technical capabilities",
  industry: "Industries served", research_interest: "Research interests", business_focus: "Business focus & priorities", interest: "Interests",
  project: "Projects", documented_collaboration: "Publicly documented collaborations", location: "Location",
};

const schema = z.object({
  field: z.enum(["product", "service", "technology", "capability", "industry", "research_interest", "business_focus", "interest", "project", "location"]),
  value: z.string().trim().min(5, "Describe it in at least 5 characters").max(1000),
  label: z.string().trim().max(200).optional(),
});
type FormValues = z.infer<typeof schema>;

export default function CompanyIntelligence() {
  const { companyId } = useWorkspace();
  const q = useProfile(companyId);
  const [changes, setChanges] = useState<RankingChange[] | null>(null);
  if (q.isLoading) return <LoadingBlock rows={6} />;
  if (q.isError) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  const p = q.data!;
  const c = p.company;
  const fields = FIELD_ORDER.filter((f) => p.groups[f]?.length || p.completeness.unknown.includes(f));

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Stage 1 · Understand the company" title={c.name}
        description={c.overview ?? undefined}
        actions={<>
          {c.website && <SourceLink href={c.website}>Official website</SourceLink>}
          <Badge tone="neutral" icon={<MapPin className="size-3" />} title={c.location?.basis}>{c.location?.label ?? "Location unknown"}</Badge>
          {c.membership_evidence && <a href={c.membership_evidence.url} target="_blank" rel="noopener noreferrer"><Badge tone="green">BSP member · verified {new Date(c.membership_evidence.retrieved_at).toLocaleDateString("en-GB")}</Badge></a>}
        </>} />

      <div className="grid gap-4 md:grid-cols-4">
        <Legend type="source_stated" text={p.legend.source_stated} count={c.stats.source_stated} />
        <Legend type="inferred" text={p.legend.inferred} count={c.stats.inferred} />
        <Legend type="user_provided" text={p.legend.user_provided} count={c.stats.user_provided} />
        <Card className="p-4">
          <div className="text-[12px] font-medium text-ink-3">Profile completeness</div>
          <div className="mt-1 text-[24px] font-semibold text-ink">{p.completeness.score_pct}%</div>
          <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-100" aria-hidden><div className="h-full rounded-full bg-series-1" style={{ width: `${p.completeness.score_pct}%` }} /></div>
          <p className="mt-2 text-[12px] text-ink-3">Unknown: {p.completeness.unknown.map((f) => FIELD_LABEL[f] ?? f).join(", ") || "none"}</p>
        </Card>
      </div>

      {changes && <RankingDiff changes={changes} />}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="space-y-4">
          {fields.map((f) => (
            <Card key={f}>
              <CardHeader title={FIELD_LABEL[f] ?? titleCase(f)} subtitle={p.groups[f]?.length ? undefined : "Not found in collected sources (unknown)"} />
              <CardBody className="space-y-2">
                {(p.groups[f] ?? []).map((claim) => <ClaimRow key={claim.id} claim={claim} companyId={companyId} onChanges={setChanges} />)}
                {!p.groups[f]?.length && <p className="text-[13px] text-ink-3">VSP did not find this information. You can add it below — it will be labelled as company-provided.</p>}
              </CardBody>
            </Card>
          ))}
        </div>
        <div className="space-y-6">
          <AddClaim companyId={companyId} onChanges={setChanges} />
          <Card>
            <CardHeader icon={<Lightbulb className="size-4" />} title="Inference rules" subtitle="Transparent rules that propose interests from source facts. They never overwrite facts." />
            <CardBody>
              <ul className="space-y-2.5">
                {p.inference_rules.filter((r) => r.status !== "not_applicable").map((r) => (
                  <li key={r.rule} className="text-[13px]">
                    <div className="flex flex-wrap items-center gap-1.5"><span className="font-medium text-ink">{r.label}</span><RuleStatus status={r.status} /></div>
                    <p className="mt-0.5 text-[12.5px] text-ink-3">{r.explanation}</p>
                  </li>
                ))}
              </ul>
            </CardBody>
          </Card>
          <Card>
            <CardHeader title="Concepts used for matching" subtitle="Derived from active claims. Strength 1.0 = source-stated; 0.5 = unconfirmed inference." />
            <CardBody className="flex flex-wrap gap-1.5">
              {p.concepts.slice(0, 30).map((k) => (
                <Badge key={k.key} tone={k.interest_only ? "amber" : k.kind === "technology" ? "brand" : k.kind === "domain" ? "teal" : "neutral"} title={`${k.kind} · strength ${k.strength}`}>
                  {k.label} · {k.strength}
                </Badge>
              ))}
            </CardBody>
          </Card>
          <Card>
            <CardHeader icon={<History className="size-4" />} title="Revision history" />
            <CardBody>
              {p.revisions.length === 0 ? <p className="text-[13px] text-ink-3">No edits yet.</p> : (
                <ul className="space-y-2 text-[12.5px]">{p.revisions.map((r) => <li key={r.id}><span className="font-medium text-ink">{titleCase(r.action)}</span><span className="text-ink-3"> · {formatDateTime(r.created_at)}</span>{r.note && <div className="text-ink-3">“{r.note}”</div>}</li>)}</ul>
              )}
            </CardBody>
          </Card>
        </div>
      </div>
    </div>
  );
}

function Legend({ type, text, count }: { type: Claim["claim_type"]; text: string; count: number }) {
  return (
    <Card className="p-4">
      <div className="flex items-center justify-between"><ClaimTypeBadge type={type} /><span className="text-[20px] font-semibold text-ink">{count}</span></div>
      <p className="mt-2 text-[12.5px] text-ink-3">{text}</p>
    </Card>
  );
}

function RuleStatus({ status }: { status: string }) {
  const map: Record<string, { t: "green" | "neutral" | "amber" | "red"; l: string }> = {
    exists: { t: "amber", l: "Applied (unconfirmed)" }, created: { t: "amber", l: "Applied" }, pending_recompute: { t: "neutral", l: "Will apply on recompute" },
    skipped_covered_by_source: { t: "green", l: "Skipped — source facts already cover it" }, skipped_rejected_by_user: { t: "red", l: "Rejected by you" },
  };
  const m = map[status] ?? { t: "neutral" as const, l: status };
  return <Badge tone={m.t}>{m.l}</Badge>;
}

function ClaimRow({ claim, companyId, onChanges }: { claim: Claim; companyId: number; onChanges: (c: RankingChange[]) => void }) {
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(claim.value);
  const review = useReviewClaim(companyId);
  const patch = usePatchProfile(companyId);
  const inactive = !claim.influences_matching;
  const doReview = async (action: string) => onChanges((await review.mutateAsync({ claimId: claim.id, action })).ranking_changes);
  const save = async () => {
    const res = await patch.mutateAsync({ corrections: [{ claim_id: claim.id, value, note: "Corrected in profile editor" }] });
    onChanges(res.ranking_changes);
    setEditing(false);
  };
  const readOnly = useReadOnly();
  const busy = review.isPending || patch.isPending || readOnly;
  return (
    <div className={cn("rounded-xl border p-3.5", inactive ? "border-dashed border-line-2 bg-slate-50/70" : "border-line")}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className={cn("text-[14px] font-medium", inactive ? "text-ink-3 line-through" : "text-ink")}>{claim.label ?? claim.value.slice(0, 80)}</span>
            <ClaimTypeBadge type={claim.claim_type} />
            {claim.status !== "active" && <Badge tone={claim.status === "confirmed" ? "green" : claim.status === "rejected" ? "red" : "neutral"}>{titleCase(claim.status)}</Badge>}
          </div>
          {!editing ? <p className="mt-1 text-[13px] leading-relaxed text-ink-2">{claim.value}</p> : (
            <div className="mt-2 space-y-2">
              <textarea value={value} onChange={(e) => setValue(e.target.value)} rows={3} className={cn(inputClass, "h-auto py-2")} aria-label="Corrected value" />
              <p className="text-[12px] text-ink-3">{claim.claim_type === "user_provided" ? "Updates your own entry." : "The original stays visible as evidence; your correction supersedes it."}</p>
              <div className="flex gap-2"><Button size="sm" onClick={save} loading={patch.isPending} disabled={value.trim().length < 5}>Save correction</Button><Button size="sm" variant="ghost" onClick={() => setEditing(false)}>Cancel</Button></div>
            </div>
          )}
          {claim.claim_type === "inferred" && claim.inference_explanation && <p className="mt-1.5 rounded-md bg-amber-50 px-2 py-1 text-[12.5px] text-amber-900">Why inferred: {claim.inference_explanation}</p>}
        </div>
        <div className="flex flex-wrap gap-1">
          {claim.status !== "confirmed" && claim.status !== "corrected" && claim.claim_type !== "source_stated" && <Button size="sm" variant="outline" icon={<Check className="size-3.5" />} onClick={() => doReview("confirm")} disabled={busy}>Confirm</Button>}
          {claim.claim_type !== "source_stated" && claim.status !== "rejected" && claim.status !== "corrected" && <Button size="sm" variant="outline" icon={<X className="size-3.5" />} onClick={() => doReview("reject")} disabled={busy}>Reject</Button>}
          {claim.claim_type === "source_stated" && claim.status === "active" && <Button size="sm" variant="ghost" icon={<Clock className="size-3.5" />} onClick={() => doReview("mark_outdated")} disabled={busy}>Outdated</Button>}
          {claim.status === "active" || claim.status === "confirmed" ? <Button size="sm" variant="ghost" icon={<Pencil className="size-3.5" />} onClick={() => setEditing(true)} disabled={busy}>Correct</Button> : null}
          {claim.status !== "active" && <Button size="sm" variant="ghost" icon={<RotateCcw className="size-3.5" />} onClick={() => doReview("restore")} disabled={busy}>Restore</Button>}
        </div>
      </div>
      {(review.isError || patch.isError) && <p role="alert" className="mt-2 text-[12.5px] text-critical">{((review.error ?? patch.error) as Error).message}</p>}
      {claim.evidence && (
        <div className="mt-2">
          <button onClick={() => setOpen((v) => !v)} aria-expanded={open} className="inline-flex items-center gap-1 text-[12.5px] font-medium text-brand hover:underline">
            <ChevronDown className={cn("size-3.5 transition", open && "rotate-180")} />{open ? "Hide evidence" : "Review evidence"}
          </button>
          {open && <ul className="mt-2"><EvidenceItem ev={claim.evidence} /></ul>}
        </div>
      )}
    </div>
  );
}

function AddClaim({ companyId, onChanges }: { companyId: number; onChanges: (c: RankingChange[]) => void }) {
  const patch = usePatchProfile(companyId);
  const readOnly = useReadOnly();
  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { field: "business_focus", value: "", label: "" } });
  const onSubmit = async (v: FormValues) => {
    const res = await patch.mutateAsync({ add_claims: [{ field: v.field, value: v.value, label: v.label || undefined }] });
    onChanges(res.ranking_changes);
    reset({ field: v.field, value: "", label: "" });
  };
  return (
    <Card>
      <CardHeader icon={<Plus className="size-4" />} title="Add information" subtitle="Priorities, products or corrections. Visible only in your workspace; labelled company-provided." />
      <CardBody>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-3" noValidate>
          <Field label="Type">
            <select {...register("field")} className={inputClass}>
              {schema.shape.field.options.map((f) => <option key={f} value={f}>{FIELD_LABEL[f] ?? f}</option>)}
            </select>
          </Field>
          <Field label="Short label (optional)"><input {...register("label")} className={inputClass} placeholder="e.g. Autonomous inspection drones" /></Field>
          <Field label="Description">
            <textarea {...register("value")} rows={3} className={cn(inputClass, "h-auto py-2")} placeholder="e.g. We are developing autonomous inspection of offshore moorings" aria-invalid={!!errors.value} />
          </Field>
          {errors.value && <p role="alert" className="text-[12.5px] text-critical">{errors.value.message}</p>}
          {patch.isError && <p role="alert" className="text-[12.5px] text-critical">{(patch.error as Error).message}</p>}
          <Button type="submit" loading={patch.isPending} disabled={readOnly} title={readOnly ? READ_ONLY_HINT : undefined} className="w-full">Add and recompute</Button>
          {readOnly && <p className="text-[12.5px] text-ink-3">{READ_ONLY_HINT}</p>}
        </form>
      </CardBody>
    </Card>
  );
}
