import { motion } from "framer-motion";
import { ArrowRight, Building2, CheckCircle2, Compass, Cpu, FileSearch, MapPin, Network, ShieldCheck, Target, Timer } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { Logo } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/primitives";
import { useCompanies, useHealth } from "@/services/queries";

const STAGES = [
  { n: 1, icon: Building2, title: "Understand the company", text: "An evidence-backed profile: every fact links to the official page it came from. Inferences are labelled, never presented as facts." },
  { n: 2, icon: Target, title: "Find opportunities", text: "Funding, programmes, test environments and events ranked with visible criteria — including regional relevance for Blekinge." },
  { n: 3, icon: Cpu, title: "Discover technologies", text: "A radar of technologies linked to the company's real capabilities, with the rule behind every ring." },
  { n: 4, icon: Network, title: "Find partners", text: "Complementary capabilities — a documented need meeting a documented offer — not shared keywords." },
  { n: 5, icon: Compass, title: "Act", text: "Three practical next steps, prioritised by transparent rules and your own priorities." },
];

export default function Landing() {
  const companies = useCompanies(true);
  const health = useHealth();
  const navigate = useNavigate();
  const demo = companies.data?.items.filter((c) => c.is_demo_company) ?? [];
  const start = () => navigate(`/app/${demo.find((c) => c.slug === "ocean-harvesting")?.id ?? demo[0]?.id ?? ""}/focus`);
  const counts = health.data?.counts;
  return (
    <div className="min-h-screen bg-white">
      <header className="bg-navy-950 text-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">
          <div className="flex items-center gap-2.5"><Logo /><span className="text-[15px] font-semibold">Virtual Science Park</span></div>
          <nav className="flex items-center gap-2">
            <Link to="/login" className="rounded-lg px-3 py-2 text-[13.5px] text-slate-300 hover:text-white">Sign in</Link>
            <Button onClick={start} disabled={!demo.length} size="sm">Open the demo</Button>
          </nav>
        </div>
        <section className="relative overflow-hidden">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(37,99,235,0.35),transparent_55%),radial-gradient(ellipse_at_bottom_left,rgba(13,148,136,0.25),transparent_50%)]" />
          <div className="relative mx-auto grid max-w-7xl gap-12 px-6 pb-20 pt-12 lg:grid-cols-[1.15fr_1fr] lg:pt-16">
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
              <div className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-3 py-1 text-[12.5px] text-teal-300"><MapPin className="size-3.5" />Built for the Blue Science Park ecosystem, Karlskrona</div>
              <h1 className="mt-5 text-4xl font-semibold leading-[1.1] tracking-tight md:text-[52px]">Discover. Connect. <span className="text-teal-300">Innovate.</span></h1>
              <p className="mt-5 max-w-xl text-[17px] leading-relaxed text-slate-300">
                A 15-person company does not have a business-intelligence team. Virtual Science Park reads the funding calls, ecosystem news and member directory for you — and tells you the three things worth your time, with the evidence behind each one.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <Button size="lg" onClick={start} disabled={!demo.length}>See Ocean Harvesting's opportunities <ArrowRight className="size-4" /></Button>
                <a href="#how"><Button size="lg" variant="outline" className="border-white/20 bg-transparent text-white hover:bg-white/10">How it works</Button></a>
              </div>
              <ul className="mt-8 grid max-w-xl gap-2 text-[13.5px] text-slate-300 sm:grid-cols-2">
                {["Every claim traced to a source", "No invented eligibility or deadlines", "Works without any AI key", "Regional relevance for Blekinge"].map((t) => <li key={t} className="flex items-center gap-2"><CheckCircle2 className="size-4 text-teal-300" />{t}</li>)}
              </ul>
            </motion.div>
            <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="rounded-2xl border border-white/10 bg-white/[0.04] p-6 backdrop-blur">
              <div className="text-[12px] font-semibold uppercase tracking-wider text-slate-400">Dataset in this demo · collected snapshot</div>
              <dl className="mt-4 grid grid-cols-2 gap-4">
                <Metric label="Blue Science Park members verified" value={counts ? counts.companies_profiled + counts.companies_directory : "—"} />
                <Metric label="Opportunity & ecosystem records" value={counts?.opportunities ?? "—"} />
                <Metric label="Cited evidence records" value={counts?.evidence ?? "—"} />
                <Metric label="Evidence-backed profiles" value={counts?.companies_profiled ?? "—"} />
              </dl>
              <p className="mt-4 text-[12px] leading-relaxed text-slate-400">Sources: Vinnova open-data API, the Blue Science Park member directory and news metadata, and official company websites. Counts come from the running database.</p>
              <div className="mt-5 space-y-2">
                {demo.map((c) => (
                  <Link key={c.id} to={`/app/${c.id}/focus`} className="flex items-center justify-between rounded-xl border border-white/10 bg-white/5 px-4 py-3 hover:bg-white/10">
                    <div><div className="text-[14px] font-medium">{c.name}</div><div className="text-[12px] text-slate-400">{c.tagline}</div></div>
                    <ArrowRight className="size-4 text-slate-400" />
                  </Link>
                ))}
              </div>
            </motion.div>
          </div>
        </section>
      </header>

      <section className="mx-auto max-w-7xl px-6 py-20">
        <div className="grid gap-10 lg:grid-cols-3">
          <div>
            <h2 className="text-[13px] font-semibold uppercase tracking-wider text-brand">The problem</h2>
            <p className="mt-3 text-2xl font-semibold leading-snug text-ink">Opportunities are scattered. Small teams miss them.</p>
          </div>
          <p className="text-[15px] leading-relaxed text-ink-2 lg:col-span-2">
            Funding calls, test environments, research programmes and potential partners are spread across funders, ecosystem newsletters and company websites. Large companies have people to follow it all. Most Blue Science Park members — many with 10–25 employees — don't. Generic AI chat answers sound plausible but can't show where a claim came from. VSP does the reading, matches it against what each company has actually published, and shows its working.
          </p>
        </div>
      </section>

      <section id="how" className="bg-canvas py-20">
        <div className="mx-auto max-w-7xl px-6">
          <h2 className="text-[13px] font-semibold uppercase tracking-wider text-brand">Five connected stages</h2>
          <p className="mt-2 max-w-2xl text-2xl font-semibold text-ink">From "what do we do?" to "what should we do next?"</p>
          <ol className="mt-10 grid gap-4 md:grid-cols-5">
            {STAGES.map((s) => (
              <li key={s.n} className="rounded-2xl border border-line bg-white p-5 shadow-[var(--shadow-card)]">
                <div className="flex items-center justify-between"><span className="flex size-8 items-center justify-center rounded-lg bg-navy-900 text-[13px] font-semibold text-white">{s.n}</span><s.icon className="size-5 text-brand" /></div>
                <h3 className="mt-4 text-[15px] font-semibold text-ink">{s.title}</h3>
                <p className="mt-1.5 text-[13px] leading-relaxed text-ink-3">{s.text}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="mx-auto grid max-w-7xl gap-6 px-6 py-20 md:grid-cols-3">
        <Feature icon={<FileSearch className="size-5" />} title="Evidence you can check" text="Each profile fact quotes its source page, with a retrieval date and an automatic check that the excerpt is still there." />
        <Feature icon={<MapPin className="size-5" />} title="Regional, not parochial" text="Local events and nearby partners rank higher when it matters; online events and national or European funding are never penalised." />
        <Feature icon={<Timer className="size-5" />} title="Time saved" text="One page, three actions, the deadlines that matter. Change a priority and watch the ranking respond." />
        <Feature icon={<ShieldCheck className="size-5" />} title="Honest about uncertainty" text="Missing eligibility, unstated deadlines and inferred interests are shown as such — never filled in." />
        <Feature icon={<Network className="size-5" />} title="Complementarity, not similarity" text="Partners are suggested only where one side's documented need meets the other's documented capability." />
        <Feature icon={<Building2 className="size-5" />} title="Private company workspace" text="One login per company. Your edits and priorities shape your results only — never another company's." />
      </section>

      <footer className="border-t border-line py-10 text-center text-[13px] text-ink-3">
        <p className="text-[15px] font-medium text-ink">Virtual Science Park transforms scattered innovation information into evidence-backed opportunities, meaningful connections, and actionable business decisions.</p>
        <p className="mt-3">BUILD Hackathon 2026 · Demonstration prototype · Not affiliated with or endorsed by the organisations whose public data it displays.</p>
      </footer>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return <div><dt className="text-[12px] text-slate-400">{label}</dt><dd className="mt-1 text-[28px] font-semibold tabular-nums">{value}</dd></div>;
}

function Feature({ icon, title, text }: { icon: React.ReactNode; title: string; text: string }) {
  return (
    <div className="rounded-2xl border border-line p-6">
      <div className="flex size-10 items-center justify-center rounded-xl bg-brand-50 text-brand">{icon}</div>
      <h3 className="mt-4 text-[15px] font-semibold text-ink">{title}</h3>
      <p className="mt-1.5 text-[13.5px] leading-relaxed text-ink-3">{text}</p>
    </div>
  );
}
