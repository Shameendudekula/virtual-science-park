import { motion } from "framer-motion";
import { ArrowRight, Bookmark, CalendarClock, Clock3, Cpu, MapPin, Sparkles, Users } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { useWorkspace } from "@/app/workspace";
import { Badge, Button, Card, CardBody, CardHeader, EmptyState, ErrorState, LoadingBlock, PageHeader } from "@/components/ui/primitives";
import { BandBadge, DeadlineBadge, LocationBadges, RingBadge, SourceLink, TierBadge } from "@/components/shared/badges";
import { PriorityEditor } from "@/features/priorities";
import { OpportunityDrawer } from "@/features/opportunity";
import { useFocus, useRecAction } from "@/services/queries";
import type { OppCard } from "@/types/api";

export default function Focus() {
  const { companyId } = useWorkspace();
  const q = useFocus(companyId);
  const act = useRecAction(companyId);
  const [openOpp, setOpenOpp] = useState<number | null>(null);
  if (q.isLoading) return <LoadingBlock rows={5} label="Finding your opportunities" />;
  if (q.isError) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  const f = q.data!;
  const base = `/app/${companyId}`;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={<span className="inline-flex items-center gap-1.5"><Sparkles className="size-3.5" />Your Innovation Opportunities</span>}
        title={<>What {f.company.name} should look at this week</>}
        description={<>Built for small teams without time to research the market. {f.time_saved.message}</>}
        actions={<Badge tone="neutral" icon={<MapPin className="size-3" />}>{f.company.location?.label ?? "Location unknown"}</Badge>}
      />

      <section aria-labelledby="top3">
        <h2 id="top3" className="mb-3 text-[13px] font-semibold uppercase tracking-wide text-ink-3">Top three things to investigate</h2>
        {f.top_three.length === 0 ? (
          <EmptyState title="No recommendations yet" description="Add priorities or profile details so VSP can match opportunities to you." action={<Link to={`${base}/company`}><Button variant="outline">Open company profile</Button></Link>} />
        ) : (
          <div className="grid gap-4 lg:grid-cols-3">
            {f.top_three.map((r, i) => (
              <motion.div key={r.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.06 }}>
                <Card className="flex h-full flex-col p-5">
                  <div className="flex items-center justify-between">
                    <span className="flex size-8 items-center justify-center rounded-full bg-navy-900 text-[14px] font-semibold text-white">{i + 1}</span>
                    <TierBadge tier={r.tier} />
                  </div>
                  <h3 className="mt-3 text-[15px] font-semibold leading-snug text-ink">{r.title}</h3>
                  {r.why[0] && <p className="mt-2 text-[13px] leading-relaxed text-ink-2"><span className="font-medium text-ink">Why it fits: </span>{r.why[0]}</p>}
                  {r.geography && "relevance_label" in r.geography && <p className="mt-2 text-[12.5px] text-ink-3"><MapPin className="mr-1 inline size-3.5 text-brand" />{r.geography.relevance_label} — {r.geography.explanation}</p>}
                  {r.geography && "label" in r.geography && !("relevance_label" in r.geography) && <p className="mt-2 text-[12.5px] text-ink-3"><MapPin className="mr-1 inline size-3.5 text-brand" />{r.geography.label}</p>}
                  <div className="mt-3 rounded-lg bg-brand-50/70 p-3 text-[13px] text-ink"><span className="font-semibold">Next step: </span>{r.next_step}</div>
                  <div className="mt-auto flex flex-wrap items-center gap-2 pt-4 text-[13px]">
                    {r.source && <SourceLink href={r.source.url}>{r.source.label}</SourceLink>}
                    <Button size="sm" variant={r.status === "saved" ? "subtle" : "outline"} className="ml-auto" icon={<Bookmark className="size-3.5" />}
                      loading={act.isPending && act.variables?.recId === r.id}
                      onClick={() => act.mutate({ recId: r.id, action: r.status === "saved" ? "restore" : "save" })}>
                      {r.status === "saved" ? "Saved" : "Save"}
                    </Button>
                  </div>
                </Card>
              </motion.div>
            ))}
          </div>
        )}
        <div className="mt-3 text-right"><Link to={`${base}/recommendations`} className="inline-flex items-center gap-1 text-[13px] font-medium text-brand hover:underline">See all recommendations and their evidence <ArrowRight className="size-3.5" /></Link></div>
      </section>

      <div className="grid gap-6 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader icon={<CalendarClock className="size-4" />} title="Deadlines that matter" subtitle="Only opportunities relevant to you, with a deadline stated in the source." />
          <CardBody>
            <OppList items={f.deadlines} onOpen={setOpenOpp} empty="No relevant deadlines in the collected data." />
          </CardBody>
        </Card>
        <Card>
          <CardHeader icon={<Clock3 className="size-4" />} title="New for you" subtitle="Opened or published in the last 45 days." />
          <CardBody>
            <OppList items={f.new_opportunities} onOpen={setOpenOpp} compact empty="Nothing new since the last collection." />
          </CardBody>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader icon={<MapPin className="size-4" />} title="Local events, test environments & programmes" subtitle="In Blekinge or online. Event dates are not in the collected metadata — open the source." />
          <CardBody><OppList items={f.local_events} onOpen={setOpenOpp} compact empty="No relevant local or online items in the collected data." /></CardBody>
        </Card>
        <Card>
          <CardHeader icon={<Users className="size-4" />} title="Companies nearby that could help" subtitle="Potential complementarities — no one has been contacted or has agreed to anything." />
          <CardBody className="space-y-3">
            {f.regional_partners.length === 0 && f.wider_partners.length === 0 && <p className="text-[13px] text-ink-3">No complementary partner found yet.</p>}
            {[...f.regional_partners, ...f.wider_partners].map((p) => (
              <div key={p.id} className="rounded-xl border border-line p-3.5">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium text-ink">{p.name}</span>
                  <Badge tone={p.location?.scopes.includes("blekinge") ? "brand" : "neutral"} icon={<MapPin className="size-3" />}>{p.location?.label ?? "Location unknown"}</Badge>
                  <Badge tone="neutral">{p.strength} · {p.score}</Badge>
                </div>
                <p className="mt-1.5 text-[13px] text-ink-2">{p.why[0]}</p>
                <p className="mt-1 text-[12.5px] text-ink-3">{p.proximity}</p>
                <p className="mt-2 text-[13px] text-ink"><span className="font-semibold">First step: </span>{p.first_step}</p>
              </div>
            ))}
            <Link to={`${base}/collaboration`} className="inline-flex items-center gap-1 text-[13px] font-medium text-brand hover:underline">Open the collaboration graph <ArrowRight className="size-3.5" /></Link>
          </CardBody>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <div className="xl:col-span-2"><PriorityEditor companyId={companyId} priorities={f.priorities} /></div>
        <div className="space-y-6">
          <Card>
            <CardHeader icon={<Cpu className="size-4" />} title="Technologies that could improve your business" />
            <CardBody className="space-y-3">
              {f.technologies.length === 0 && <p className="text-[13px] text-ink-3">No technology reached the trial ring.</p>}
              {f.technologies.map((t) => (
                <div key={t.key}>
                  <div className="flex items-center gap-2"><span className="font-medium text-ink">{t.name}</span><RingBadge ring={t.ring} /></div>
                  <p className="mt-1 text-[13px] text-ink-2">{t.next_step}</p>
                </div>
              ))}
            </CardBody>
          </Card>
          <Card>
            <CardHeader icon={<Bookmark className="size-4" />} title="Saved" subtitle={`${f.saved_count} saved item${f.saved_count === 1 ? "" : "s"}`} />
            <CardBody>
              {f.saved.length === 0 ? <p className="text-[13px] text-ink-3">Save recommendations to build your shortlist.</p> :
                <ul className="space-y-1.5 text-[13px]">{f.saved.map((s) => <li key={s.id} className="text-ink">{s.title}</li>)}</ul>}
            </CardBody>
          </Card>
          <p className="text-[12px] text-ink-3">Data: {f.freshness}.</p>
        </div>
      </div>
      <OpportunityDrawer id={openOpp} companyId={companyId} onClose={() => setOpenOpp(null)} />
    </div>
  );
}

function OppList({ items, onOpen, empty, compact }: { items: OppCard[]; onOpen: (id: number) => void; empty: string; compact?: boolean }) {
  if (!items.length) return <p className="text-[13px] text-ink-3">{empty}</p>;
  return (
    <ul className="divide-y divide-line">
      {items.map((o) => (
        <li key={o.id} className="py-3 first:pt-0 last:pb-0">
          <button onClick={() => onOpen(o.id)} className="w-full text-left">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-[14px] font-medium text-ink hover:text-brand">{o.title}</span>
            </div>
            <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
              <BandBadge band={o.band} score={o.score} />
              {o.deadline_at && <DeadlineBadge deadline={o.deadline_at} days={o.days_left} />}
              <LocationBadges scopes={o.geography.scopes} inferred={o.geography.inferred} />
              {!compact && <span className="text-[12px] text-ink-3">{o.organisation}</span>}
            </div>
            {!compact && o.why[0] && <p className="mt-1 text-[12.5px] text-ink-3">{o.why[0]}</p>}
          </button>
        </li>
      ))}
    </ul>
  );
}
