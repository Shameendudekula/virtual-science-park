import { Activity, ArrowRight, Building2, CalendarClock, Compass, Cpu, Database, ListChecks, Network, Target } from "lucide-react";
import { Link } from "react-router-dom";
import { useReadOnly, useWorkspace } from "@/app/workspace";
import { Badge, Card, CardBody, CardHeader, ErrorState, LoadingBlock, PageHeader, Stat } from "@/components/ui/primitives";
import { BandBadge, RingBadge, StatusPill, TierBadge } from "@/components/shared/badges";
import { useOverview } from "@/services/queries";
import { deadlineGroup, formatDate, formatDateTime, relativeDays } from "@/lib/utils";
import type { OverviewResponse } from "@/types/api";

const STAGES = [
  { n: 1, to: "company", label: "Understand the company", icon: Building2 },
  { n: 2, to: "opportunities", label: "Find opportunities", icon: Target },
  { n: 3, to: "technologies", label: "Discover technologies", icon: Cpu },
  { n: 4, to: "collaboration", label: "Find partners", icon: Network },
  { n: 5, to: "recommendations", label: "Act on recommendations", icon: Compass },
];

type NextStep = { key: string; title: string; text: string; to: string; action: string };

/** Up to three concrete actions derived only from the overview data the API already returned.
 * Read-only (demo) visitors are only pointed at things they can do: viewing, not confirming or editing. */
function nextSteps(d: OverviewResponse, base: string, readOnly: boolean): NextStep[] {
  const steps: NextStep[] = [];
  const pending = d.profile.pending_review;
  if (readOnly && pending > 0) {
    steps.push({ key: "profile", title: "See how the profile was built", text: `${pending} ${pending === 1 ? "item is" : "items are"} inferred, not verified facts. Check the sources behind each claim.`, to: `${base}/company`, action: "View profile" });
  } else if (readOnly && d.profile.completeness < 80) {
    steps.push({ key: "profile", title: "See what the profile documents", text: `The profile is ${d.profile.completeness}% complete. Missing information is listed with each section.`, to: `${base}/company`, action: "View profile" });
  } else if (pending > 0) {
    steps.push({ key: "profile", title: `Review ${pending} inferred profile ${pending === 1 ? "item" : "items"}`, text: "Inferred items are not verified facts. Confirm or correct them to improve every match.", to: `${base}/company`, action: "Review profile" });
  } else if (d.profile.completeness < 80) {
    steps.push({ key: "profile", title: "Complete your company profile", text: `Your profile is ${d.profile.completeness}% complete. More documented capabilities give better matches.`, to: `${base}/company`, action: "Open profile" });
  }
  const next = d.deadlines.find((x) => deadlineGroup(x.deadline_at, x.days_left) === "upcoming");
  if (next) {
    const left = relativeDays(next.days_left);
    steps.push({ key: "deadline", title: `Next deadline: ${formatDate(next.deadline_at)}${left ? ` (${left})` : ""}`, text: next.title, to: `${base}/opportunities?view=timeline`, action: "See all deadlines" });
  } else if (d.metrics.relevant_opportunities > 0) {
    steps.push({ key: "opps", title: `Review ${d.metrics.relevant_opportunities} relevant opportunities`, text: `Screened from ${d.metrics.opportunities_considered} collected opportunities.`, to: `${base}/opportunities`, action: "Browse opportunities" });
  }
  const partner = d.partners[0];
  if (partner) {
    steps.push({ key: "partner", title: `Look at a potential partner: ${partner.name}`, text: partner.headline, to: `${base}/collaboration`, action: "View potential partners" });
  }
  const rec = d.top_recommendations[0];
  if (rec) {
    const verb = readOnly ? "Review" : "Act on";
    steps.push({ key: "rec", title: d.metrics.high_priority_actions > 0 ? `${verb} ${d.metrics.high_priority_actions} high-priority recommendations` : "Review your recommendations", text: `Start with: ${rec.title}`, to: `${base}/recommendations`, action: "Open recommendations" });
  }
  if (steps.length === 0) {
    steps.push({ key: "opps", title: "Explore opportunities", text: "Browse funding, programmes and events ranked for your company.", to: `${base}/opportunities`, action: "Browse opportunities" });
  }
  return steps.slice(0, 3);
}

function NextSteps({ steps }: { steps: NextStep[] }) {
  return (
    <Card>
      <CardHeader icon={<ListChecks className="size-4" />} title="Your next steps" subtitle="Suggested from your profile, deadlines and potential partners." />
      <CardBody>
        <ol className="grid gap-3 md:grid-cols-3">
          {steps.map((s, i) => (
            <li key={s.key} className="flex flex-col rounded-xl border border-line p-4">
              <div className="flex items-start gap-2.5">
                <span className="flex size-6 shrink-0 items-center justify-center rounded-md bg-brand text-[12px] font-semibold text-white" aria-hidden>{i + 1}</span>
                <h3 className="text-[14px] font-semibold leading-snug text-ink">{s.title}</h3>
              </div>
              <p className="mt-1.5 line-clamp-2 pl-[34px] text-[13px] text-ink-2">{s.text}</p>
              <Link to={s.to} className="mt-auto inline-flex items-center gap-1 pl-[34px] pt-3 text-[13px] font-medium text-brand hover:underline">
                {s.action} <ArrowRight className="size-3.5" aria-hidden />
              </Link>
            </li>
          ))}
        </ol>
      </CardBody>
    </Card>
  );
}

export default function Overview() {
  const { companyId } = useWorkspace();
  const readOnly = useReadOnly();
  const q = useOverview(companyId);
  if (q.isLoading) return <LoadingBlock rows={5} />;
  if (q.isError) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  const d = q.data!;
  const base = `/app/${companyId}`;
  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Overview" title={d.company.name} description={d.profile.overview ?? d.company.tagline ?? undefined}
        actions={<Badge tone={d.company.membership_status === "verified" ? "green" : "amber"}>{d.company.membership_status === "verified" ? "Blue Science Park member · verified" : "Membership unverified"}</Badge>} />

      <NextSteps steps={nextSteps(d, base, readOnly)} />

      <Card className="overflow-hidden">
        <div className="bg-gradient-to-r from-navy-900 to-navy-700 px-6 py-5 text-white">
          <div className="text-[12px] font-semibold uppercase tracking-wider text-teal-300">Executive summary · under one minute</div>
          <h2 className="mt-1 text-[19px] font-semibold">{d.summary.headline}</h2>
          <ul className="mt-3 space-y-1.5 text-[14px] text-slate-200">{d.summary.bullets.map((b) => <li key={b} className="flex gap-2"><span className="text-teal-300">•</span>{b}</li>)}</ul>
          <p className="mt-3 text-[11.5px] text-slate-400">Generated by a deterministic template over application records · as of {formatDate(d.summary.as_of)}</p>
        </div>
        <ol className="grid grid-cols-2 divide-line border-t border-line sm:grid-cols-5 sm:divide-x">
          {STAGES.map((s) => (
            <li key={s.n}>
              <Link to={`${base}/${s.to}`} className="flex h-full items-center gap-2.5 px-4 py-3 text-[13px] hover:bg-canvas">
                <span className="flex size-6 items-center justify-center rounded-md bg-brand-50 text-[12px] font-semibold text-brand">{s.n}</span>
                <span className="font-medium text-ink">{s.label}</span>
              </Link>
            </li>
          ))}
        </ol>
      </Card>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
        <Stat label="Relevant opportunities" value={d.metrics.relevant_opportunities} hint={`of ${d.metrics.opportunities_considered} screened`} icon={<Target className="size-4" />} />
        <Stat label="High-priority actions" value={d.metrics.high_priority_actions} hint="rule-based tiers" icon={<Compass className="size-4" />} />
        <Stat label="Technologies to adopt/trial" value={d.metrics.technologies_adopt_trial} icon={<Cpu className="size-4" />} />
        <Stat label="Potential partners" value={d.metrics.potential_partners} hint="complementarity ≥ 25" icon={<Network className="size-4" />} />
        <Stat label="Profile completeness" value={`${d.profile.completeness}%`} hint={`${d.profile.claims_by_type.source_stated} sourced · ${d.profile.claims_by_type.inferred} inferred`} icon={<Building2 className="size-4" />} />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader icon={<Compass className="size-4" />} title="Top actionable recommendations" action={<Link to={`${base}/recommendations`} className="text-[13px] font-medium text-brand hover:underline">All</Link>} />
          <CardBody>
            <ul className="divide-y divide-line">
              {d.top_recommendations.map((r) => (
                <li key={r.id} className="flex items-center justify-between gap-3 py-2.5">
                  <span className="text-[14px] text-ink">{r.title}</span>
                  <TierBadge tier={r.tier} />
                </li>
              ))}
            </ul>
          </CardBody>
        </Card>
        <Card>
          <CardHeader icon={<CalendarClock className="size-4" />} title="Upcoming deadlines" />
          <CardBody>
            {d.deadlines.length === 0 ? <p className="text-[13px] text-ink-3">No relevant deadline stated in collected sources.</p> : (
              <ol className="relative space-y-3 border-l border-line pl-4">
                {d.deadlines.map((x) => (
                  <li key={x.id}>
                    <span className="absolute -left-[5px] mt-1.5 size-2.5 rounded-full bg-series-1" aria-hidden />
                    <div className="text-[12px] font-semibold text-ink-2">{formatDate(x.deadline_at)}{relativeDays(x.days_left) ? ` · ${relativeDays(x.days_left)}` : ""}</div>
                    <div className="text-[13px] text-ink">{x.title}</div>
                  </li>
                ))}
              </ol>
            )}
          </CardBody>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card>
          <CardHeader icon={<Target className="size-4" />} title="Relevant opportunities" action={<Link to={`${base}/opportunities`} className="text-[13px] font-medium text-brand hover:underline">Radar</Link>} />
          <CardBody>
            <ul className="space-y-2.5">{d.top_opportunities.map((o) => <li key={o.id}><div className="text-[13.5px] text-ink">{o.title}</div><div className="mt-0.5 flex gap-1.5"><BandBadge band={o.band} score={o.score} /><span className="text-[12px] text-ink-3">{o.timeliness.label}</span></div></li>)}</ul>
          </CardBody>
        </Card>
        <Card>
          <CardHeader icon={<Cpu className="size-4" />} title="Technology recommendations" action={<Link to={`${base}/technologies`} className="text-[13px] font-medium text-brand hover:underline">Radar</Link>} />
          <CardBody>
            <ul className="space-y-2">{d.technologies.map((t) => <li key={t.key} className="flex items-center justify-between gap-2"><span className="text-[13.5px] text-ink">{t.name}<span className="ml-1 text-[12px] text-ink-3">({t.relation})</span></span><RingBadge ring={t.ring} /></li>)}</ul>
          </CardBody>
        </Card>
        <Card>
          <CardHeader icon={<Network className="size-4" />} title="Potential partners" action={<Link to={`${base}/collaboration`} className="text-[13px] font-medium text-brand hover:underline">All partners</Link>} />
          <CardBody>
            <ul className="space-y-2.5">{d.partners.map((p) => <li key={p.id}><div className="flex items-center gap-2 text-[13.5px] font-medium text-ink">{p.name}<Badge tone="neutral">{p.strength}</Badge></div><p className="text-[12.5px] text-ink-3 line-clamp-2">{p.headline}</p></li>)}</ul>
          </CardBody>
        </Card>
      </div>

      <Card>
        <CardHeader icon={<Database className="size-4" />} title="Data freshness & source health" subtitle={d.freshness.label} action={<Link to={`${base}/sources`} className="text-[13px] font-medium text-brand hover:underline">Data Sources</Link>} />
        <CardBody className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {d.freshness.sources.map((s) => (
            <div key={s.key} className="rounded-xl border border-line p-3">
              <div className="flex items-center justify-between gap-2"><span className="text-[13px] font-medium text-ink">{s.name.split("—")[0]}</span><StatusPill status={s.status} /></div>
              <div className="mt-1 flex items-center gap-1 text-[12px] text-ink-3"><Activity className="size-3" />Last live success: {formatDateTime(s.last_success_at)}</div>
            </div>
          ))}
        </CardBody>
      </Card>
      <Link to={`${base}/brief`} className="inline-flex items-center gap-1 text-[13px] font-medium text-brand hover:underline">Generate the innovation brief <ArrowRight className="size-3.5" /></Link>
    </div>
  );
}
