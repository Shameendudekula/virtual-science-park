import { AnimatePresence, motion } from "framer-motion";
import {
  Bell, BookOpen, Building2, ChevronDown, Compass, Cpu, Database, FileText, GitCompareArrows, LayoutDashboard, LogOut, Menu,
  Network, Search, Settings, Sparkles, Target, Users, X,
} from "lucide-react";
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useWorkspace } from "@/app/workspace";
import { Badge } from "@/components/ui/primitives";
import { useCompanies, useCompany, useHealth, useNotifications } from "@/services/queries";
import { cn, formatDateTime } from "@/lib/utils";

interface NavItem { to: string; label: string; icon: ReactNode; stage?: number }

function nav(id: number): { group: string; items: NavItem[] }[] {
  const p = `/app/${id}`;
  return [
    { group: "Start here", items: [{ to: `${p}/focus`, label: "Your Opportunities", icon: <Sparkles className="size-4" /> }, { to: `${p}/overview`, label: "Overview", icon: <LayoutDashboard className="size-4" /> }] },
    {
      group: "Five-stage workflow",
      items: [
        { to: `${p}/company`, label: "Company Intelligence", icon: <Building2 className="size-4" />, stage: 1 },
        { to: `${p}/opportunities`, label: "Opportunity Radar", icon: <Target className="size-4" />, stage: 2 },
        { to: `${p}/technologies`, label: "Technology Radar", icon: <Cpu className="size-4" />, stage: 3 },
        { to: `${p}/collaboration`, label: "Collaboration Graph", icon: <Network className="size-4" />, stage: 4 },
        { to: `${p}/recommendations`, label: "Recommendations", icon: <Compass className="size-4" />, stage: 5 },
      ],
    },
    {
      group: "Tools",
      items: [
        { to: `${p}/compare`, label: "Compare companies", icon: <GitCompareArrows className="size-4" /> },
        { to: `${p}/brief`, label: "Innovation brief", icon: <FileText className="size-4" /> },
        { to: `${p}/search`, label: "Ask VSP", icon: <Search className="size-4" /> },
      ],
    },
    {
      group: "Ecosystem & data",
      items: [
        { to: `${p}/members`, label: "Member directory", icon: <Users className="size-4" /> },
        { to: `${p}/sources`, label: "Data Sources", icon: <Database className="size-4" /> },
        { to: `${p}/settings`, label: "Settings", icon: <Settings className="size-4" /> },
      ],
    },
  ];
}

function Sidebar({ id, onNavigate }: { id: number; onNavigate?: () => void }) {
  return (
    <nav aria-label="Workspace" className="flex h-full flex-col bg-navy-900 text-slate-300">
      <Link to="/" className="flex items-center gap-2.5 px-5 py-5" onClick={onNavigate}>
        <Logo />
        <div>
          <div className="text-[14px] font-semibold text-white">Virtual Science Park</div>
          <div className="text-[11px] text-slate-400">Discover. Connect. Innovate.</div>
        </div>
      </Link>
      <div className="flex-1 space-y-5 overflow-y-auto px-3 pb-6">
        {nav(id).map((g) => (
          <div key={g.group}>
            <div className="px-3 pb-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-500">{g.group}</div>
            <ul className="space-y-0.5">
              {g.items.map((it) => (
                <li key={it.to}>
                  <NavLink
                    to={it.to}
                    onClick={onNavigate}
                    className={({ isActive }) => cn("group flex items-center gap-2.5 rounded-lg px-3 py-2 text-[13.5px] transition",
                      isActive ? "bg-white/10 font-medium text-white" : "hover:bg-white/5 hover:text-white")}
                  >
                    {it.stage ? <span className="flex size-5 items-center justify-center rounded-md bg-white/10 text-[11px] font-semibold text-teal-300">{it.stage}</span> : it.icon}
                    <span className="flex-1">{it.label}</span>
                    {it.stage && <span className="text-slate-500 group-hover:text-slate-300">{it.icon}</span>}
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div className="border-t border-white/10 px-5 py-4 text-[11.5px] leading-relaxed text-slate-400">
        Evidence-backed suggestions. Scores are explainable heuristics, not probabilities.
      </div>
    </nav>
  );
}

export function Logo({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={cn("size-8", className)} aria-hidden>
      <rect width="32" height="32" rx="8" fill="#12274a" />
      <circle cx="16" cy="16" r="9" fill="none" stroke="#3b82f6" strokeWidth="2.5" />
      <circle cx="16" cy="16" r="3.5" fill="#2dd4bf" />
      <circle cx="25" cy="16" r="1.8" fill="#93c5fd" />
    </svg>
  );
}

function CompanySwitcher() {
  const { companyId } = useWorkspace();
  const { data } = useCompanies(true);
  const navigate = useNavigate();
  const location = useLocation();
  const section = location.pathname.split("/")[3] ?? "focus";
  return (
    <label className="relative flex min-w-0 items-center">
      <span className="sr-only">Company workspace</span>
      <Building2 className="pointer-events-none absolute left-3 size-4 text-ink-3" aria-hidden />
      <select
        value={companyId}
        onChange={(e) => navigate(`/app/${e.target.value}/${section}`)}
        className="h-10 w-full min-w-0 appearance-none rounded-lg border border-line-2 bg-white pl-9 pr-9 text-sm font-medium text-ink focus:border-brand focus:outline-none sm:w-64"
      >
        {data?.items.map((c) => (
          <option key={c.id} value={c.id}>{c.name}{c.is_demo_company ? "" : " (partial profile)"}</option>
        ))}
      </select>
      <ChevronDown className="pointer-events-none absolute right-3 size-4 text-ink-3" aria-hidden />
    </label>
  );
}

function GlobalSearch() {
  const { companyId } = useWorkspace();
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (q.trim().length >= 2) navigate(`/app/${companyId}/search?q=${encodeURIComponent(q.trim())}`);
  };
  return (
    <form onSubmit={submit} role="search" className="relative hidden flex-1 md:block md:max-w-md">
      <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-ink-3" aria-hidden />
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Ask: which funding fits us? who could we partner with?"
        aria-label="Ask VSP a question"
        className="h-10 w-full rounded-lg border border-line-2 bg-canvas pl-9 pr-3 text-sm placeholder:text-ink-3 focus:border-brand focus:bg-white focus:outline-none"
      />
    </form>
  );
}

function Notifications() {
  const { data } = useNotifications();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const onClick = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && setOpen(false);
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);
  const errors = data?.filter((n) => n.level === "error").length ?? 0;
  return (
    <div className="relative" ref={ref}>
      <button onClick={() => setOpen((v) => !v)} aria-expanded={open} aria-label="Source updates" className="relative rounded-lg p-2 text-ink-2 hover:bg-canvas">
        <Bell className="size-5" />
        {!!data?.length && <span className={cn("absolute right-1.5 top-1.5 size-2 rounded-full", errors ? "bg-critical" : "bg-brand")} />}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }}
            className="absolute right-0 z-40 mt-2 w-80 rounded-xl border border-line bg-white p-2 shadow-[var(--shadow-lift)]">
            <div className="px-2 py-1.5 text-[12px] font-semibold uppercase tracking-wide text-ink-3">Source updates</div>
            {!data?.length && <p className="px-2 py-3 text-[13px] text-ink-3">No collection runs yet.</p>}
            <ul className="max-h-80 overflow-y-auto">
              {data?.map((n) => (
                <li key={n.id} className="rounded-lg px-2 py-2 hover:bg-canvas">
                  <p className={cn("text-[13px]", n.level === "error" ? "text-critical" : "text-ink")}>{n.message}</p>
                  <p className="text-[11.5px] text-ink-3">{formatDateTime(n.at)} · {n.mode}</p>
                </li>
              ))}
            </ul>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export function AppShell() {
  const { companyId, companyName, signOut } = useWorkspace();
  const [mobileOpen, setMobileOpen] = useState(false);
  const health = useHealth();
  const company = useCompany(companyId);
  const location = useLocation();
  useEffect(() => setMobileOpen(false), [location.pathname]);
  return (
    <div className="flex min-h-screen">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-white focus:px-3 focus:py-2">Skip to content</a>
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 lg:block"><Sidebar id={companyId} /></aside>
      <AnimatePresence>
        {mobileOpen && (
          <div className="fixed inset-0 z-50 lg:hidden">
            <motion.div className="absolute inset-0 bg-navy-950/50" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setMobileOpen(false)} />
            <motion.aside className="absolute inset-y-0 left-0 w-72" initial={{ x: -280 }} animate={{ x: 0 }} exit={{ x: -280 }} transition={{ type: "spring", damping: 30, stiffness: 300 }}>
              <button onClick={() => setMobileOpen(false)} aria-label="Close menu" className="absolute right-3 top-5 z-10 rounded-lg p-1 text-slate-300 hover:bg-white/10"><X className="size-5" /></button>
              <Sidebar id={companyId} onNavigate={() => setMobileOpen(false)} />
            </motion.aside>
          </div>
        )}
      </AnimatePresence>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="no-print sticky top-0 z-30 flex items-center gap-3 border-b border-line bg-white/90 px-4 py-3 backdrop-blur md:px-6">
          <button className="rounded-lg p-2 text-ink-2 hover:bg-canvas lg:hidden" aria-label="Open menu" onClick={() => setMobileOpen(true)}><Menu className="size-5" /></button>
          <CompanySwitcher />
          <GlobalSearch />
          <div className="ml-auto flex items-center gap-1">
            {health.data && (
              <Badge tone={health.data.llm.enabled ? "teal" : "neutral"} className="hidden xl:inline-flex" title="The matching engine is deterministic; an LLM only rewords text when configured">
                {health.data.llm.enabled ? "LLM wording on" : "Deterministic engine · no LLM"}
              </Badge>
            )}
            <Link to={`/app/${companyId}/sources`} className="hidden rounded-lg p-2 text-ink-2 hover:bg-canvas sm:block" aria-label="Data sources"><BookOpen className="size-5" /></Link>
            <Notifications />
            <div className="ml-1 hidden items-center gap-2 rounded-lg border border-line px-2.5 py-1.5 sm:flex">
              <div className="flex size-7 items-center justify-center rounded-md bg-navy-900 text-[12px] font-semibold text-white">{companyName.split(/\s+/).filter((w) => /^[A-Za-zÅÄÖ]/.test(w)).slice(0, 2).map((w) => w[0]).join("").toUpperCase()}</div>
              <div className="leading-tight">
                <div className="max-w-40 truncate text-[12.5px] font-medium text-ink">{companyName}</div>
                <div className="text-[11px] text-ink-3">{company.data?.location?.label ?? "Company workspace"}</div>
              </div>
              <button onClick={signOut} className="ml-1 rounded p-1 text-ink-3 hover:bg-canvas hover:text-ink" aria-label="Sign out" title="Sign out"><LogOut className="size-4" /></button>
            </div>
          </div>
        </header>
        <main id="main" className="mx-auto w-full max-w-[1400px] flex-1 px-4 py-6 md:px-8 md:py-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
