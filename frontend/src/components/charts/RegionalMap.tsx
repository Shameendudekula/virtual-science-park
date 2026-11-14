import { useMemo, useState } from "react";
import type { GeoScope } from "@/types/api";
import { cn } from "@/lib/utils";

export interface RegionalItem {
  id: string;
  label: string;
  kind: "opportunity" | "event" | "partner";
  scopes: GeoScope[];
  inferred?: boolean;
  score: number;
  onSelect?: () => void;
}

const KIND = {
  opportunity: { color: "var(--color-series-1)", label: "Funding & programmes" },
  partner: { color: "var(--color-series-2)", label: "Potential partners" },
  event: { color: "var(--color-series-3)", label: "Events & test environments" },
} as const;

const BANDS: { scope: "karlskrona" | "blekinge" | "sweden" | "wider"; label: string; r0: number; r1: number }[] = [
  { scope: "karlskrona", label: "Karlskrona", r0: 0, r1: 92 },
  { scope: "blekinge", label: "Blekinge", r0: 92, r1: 130 },
  { scope: "sweden", label: "Sweden", r0: 130, r1: 166 },
  { scope: "wider", label: "Europe & international", r0: 166, r1: 200 },
];

function band(scopes: GeoScope[]): "karlskrona" | "blekinge" | "sweden" | "wider" | "online" | "unknown" {
  if (scopes.includes("karlskrona")) return "karlskrona";
  if (scopes.includes("blekinge")) return "blekinge";
  if (scopes.includes("europe") || scopes.includes("international")) return scopes.includes("sweden") && !scopes.includes("international") ? "sweden" : "wider";
  if (scopes.includes("sweden")) return "sweden";
  if (scopes.includes("online")) return "online";
  return "unknown";
}

/** Schematic distance-from-home diagram. Positions encode *geographic scope*, not coordinates. */
export function RegionalMap({ items, homeLabel }: { items: RegionalItem[]; homeLabel: string }) {
  const [hover, setHover] = useState<string | null>(null);
  const placed = useMemo(() => {
    const groups: Record<string, RegionalItem[]> = {};
    items.forEach((it) => (groups[band(it.scopes)] ??= []).push(it));
    const out: (RegionalItem & { x: number; y: number; n: number; band: string })[] = [];
    let n = 1;
    for (const b of BANDS) {
      const list = groups[b.scope] ?? [];
      list.forEach((it, i) => {
        // Karlskrona holds many items: two staggered sub-rings keep markers apart.
        const inner = b.scope === "karlskrona" && list.length > 8;
        const perRing = inner ? Math.ceil(list.length / 2) : list.length;
        const ringIdx = inner ? Math.floor(i / perRing) : 0;
        const j = inner ? i % perRing : i;
        const angle = -Math.PI / 2 + ((j + 0.5 + ringIdx * 0.5) / Math.max(perRing, 1)) * Math.PI * 2;
        const r = b.scope === "karlskrona" ? (inner ? [44, 72][ringIdx] : list.length === 1 ? 26 : 58) : (b.r0 + b.r1) / 2;
        out.push({ ...it, x: 220 + r * Math.cos(angle), y: 210 + r * Math.sin(angle), n: n++, band: b.scope });
      });
    }
    const online = groups.online ?? [];
    online.forEach((it, i) => out.push({ ...it, x: 470, y: 60 + i * 34, n: n++, band: "online" }));
    const unknown = groups.unknown ?? [];
    unknown.forEach((it, i) => out.push({ ...it, x: 470, y: 290 + i * 34, n: n++, band: "unknown" }));
    return out;
  }, [items]);
  const active = placed.find((p) => p.id === hover);

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_280px]">
      <div className="relative">
        <svg viewBox="0 0 540 420" className="h-auto w-full" role="img" aria-label={`Regional opportunity map around ${homeLabel}`}>
          {[...BANDS].reverse().map((b, i) => (
            <circle key={b.scope} cx={220} cy={210} r={b.r1} fill={i % 2 ? "#f8fafc" : "#ffffff"} stroke="#e2e8f0" strokeWidth={1} />
          ))}
          {BANDS.map((b) => (
            <text key={b.scope} x={220} y={210 - b.r1 + 14} textAnchor="middle" className="fill-[#5b6b82] text-[10.5px] font-medium">{b.label}</text>
          ))}
          <circle cx={220} cy={210} r={5} fill="#0b1b33" />
          <text x={220} y={232} textAnchor="middle" className="fill-[#0b1b33] text-[10px] font-semibold">{homeLabel}</text>
          <rect x={445} y={30} width={50} height={210} rx={10} fill="#ecfdf8" stroke="#99f6e4" />
          <text x={470} y={24} textAnchor="middle" className="fill-[#0d9488] text-[10.5px] font-semibold">Online</text>
          <rect x={445} y={262} width={50} height={130} rx={10} fill="#f8fafc" stroke="#e2e8f0" />
          <text x={470} y={256} textAnchor="middle" className="fill-[#5b6b82] text-[10.5px] font-medium">Not stated</text>
          {placed.map((p) => (
            <g key={p.id} transform={`translate(${p.x} ${p.y})`} role="button" tabIndex={0} aria-label={`${p.n}. ${p.label}`}
              onMouseEnter={() => setHover(p.id)} onMouseLeave={() => setHover(null)} onFocus={() => setHover(p.id)} onBlur={() => setHover(null)}
              onClick={p.onSelect} onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && p.onSelect?.()} className="cursor-pointer outline-none">
              <circle r={14} fill="transparent" />
              <circle r={hover === p.id ? 11 : 9} fill={KIND[p.kind].color} stroke="#fff" strokeWidth={2} strokeDasharray={p.inferred ? "3 2" : undefined} />
              <text textAnchor="middle" dy="3.5" className="pointer-events-none fill-white text-[9.5px] font-bold">{p.n}</text>
            </g>
          ))}
        </svg>
        {active && (
          <div className="pointer-events-none absolute left-2 top-2 max-w-xs rounded-lg border border-line bg-white px-3 py-2 text-[12.5px] shadow-[var(--shadow-lift)]">
            <div className="font-medium text-ink">{active.n}. {active.label}</div>
            <div className="text-ink-3">{KIND[active.kind].label} · relevance {active.score}{active.inferred ? " · location inferred" : ""}</div>
          </div>
        )}
        <div className="mt-2 flex flex-wrap gap-3 text-[12px] text-ink-2" aria-label="Legend">
          {Object.entries(KIND).map(([k, v]) => <span key={k} className="inline-flex items-center gap-1.5"><span className="size-2.5 rounded-full" style={{ background: v.color }} />{v.label}</span>)}
          <span className="inline-flex items-center gap-1.5"><span className="size-2.5 rounded-full border border-dashed border-ink-3" />Dashed = location inferred</span>
        </div>
      </div>
      <ol className="max-h-[420px] space-y-1 overflow-y-auto pr-1 text-[13px]" aria-label="Map items">
        {placed.map((p) => (
          <li key={p.id}>
            <button onClick={p.onSelect} onMouseEnter={() => setHover(p.id)} onMouseLeave={() => setHover(null)}
              className={cn("flex w-full items-start gap-2 rounded-lg px-2 py-1.5 text-left hover:bg-canvas", hover === p.id && "bg-canvas")}>
              <span className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold text-white" style={{ background: KIND[p.kind].color }}>{p.n}</span>
              <span className="min-w-0">
                <span className="line-clamp-2 text-ink">{p.label}</span>
                <span className="text-[11.5px] capitalize text-ink-3">{p.band === "wider" ? "Europe & international" : p.band}</span>
              </span>
            </button>
          </li>
        ))}
      </ol>
    </div>
  );
}
