import { useMemo, useState } from "react";
import type { Ring, TechItem } from "@/types/api";
import { cn } from "@/lib/utils";

const RINGS: Ring[] = ["adopt", "trial", "assess", "monitor"];
const RING_R = [100, 152, 196, 232];
export const AREA_COLORS: Record<string, string> = {
  "Digital & AI": "var(--color-series-1)",
  "Connectivity & Infrastructure": "var(--color-series-2)",
  "Energy & Climate": "var(--color-series-3)",
  "Industrial & Materials": "var(--color-series-4)",
};

export function TechRadar({ items, areas, selected, onSelect }: { items: TechItem[]; areas: string[]; selected?: string | null; onSelect: (key: string) => void }) {
  const [hover, setHover] = useState<string | null>(null);
  const C = 250;
  const placed = useMemo(() => {
    const numbered = [...items].sort((a, b) => areas.indexOf(a.area) - areas.indexOf(b.area) || RINGS.indexOf(a.ring) - RINGS.indexOf(b.ring) || b.score - a.score);
    return numbered.map((t, idx) => {
      const q = Math.max(0, areas.indexOf(t.area));
      const ringIdx = RINGS.indexOf(t.ring);
      const peers = numbered.filter((x) => x.area === t.area && x.ring === t.ring);
      const k = peers.indexOf(t);
      const a0 = (q * Math.PI) / 2 + 0.18;
      const a1 = ((q + 1) * Math.PI) / 2 - 0.18;
      const angle = a0 + ((k + 0.5) / peers.length) * (a1 - a0) - Math.PI;
      const r0 = ringIdx === 0 ? 40 : RING_R[ringIdx - 1] + 14;
      const r1 = RING_R[ringIdx] - 14;
      const r = r0 + (peers.length > 2 ? ((k % 2) * 0.7 + 0.15) : 0.55) * (r1 - r0);
      return { ...t, n: idx + 1, x: C + r * Math.cos(angle), y: C + r * Math.sin(angle) };
    });
  }, [items, areas]);
  const active = placed.find((p) => p.key === hover);

  return (
    <div className="relative">
      <svg viewBox="0 0 500 500" className="mx-auto h-auto w-full max-w-[560px]" role="img" aria-label="Technology radar: rings are recommendations (adopt, trial, assess, monitor), quadrants are technology areas">
        {[...RING_R].reverse().map((r, i) => (
          <circle key={r} cx={C} cy={C} r={r} fill={["#f8fafc", "#f1f5f9", "#eef2f7", "#e8eef6"][i]} stroke="#dbe2ec" />
        ))}
        <line x1={C - 232} y1={C} x2={C + 232} y2={C} stroke="#dbe2ec" />
        <line x1={C} y1={C - 232} x2={C} y2={C + 232} stroke="#dbe2ec" />
        {RINGS.map((ring, i) => (
          <text key={ring} x={C + 4} y={C - RING_R[i] + 13} className="fill-[#5b6b82] text-[10px] font-semibold uppercase tracking-wider">{ring}</text>
        ))}
        {areas.map((area, q) => {
          const pos = [[14, 18, "start"], [486, 18, "end"], [486, 492, "end"], [14, 492, "start"]][q] as [number, number, "start" | "end"];
          return <text key={area} x={pos[0]} y={pos[1]} textAnchor={pos[2]} className="fill-[#334155] text-[11.5px] font-semibold">{area}</text>;
        })}
        {placed.map((p) => {
          const isActive = p.key === (hover ?? selected);
          return (
            <g key={p.key} transform={`translate(${p.x} ${p.y})`} role="button" tabIndex={0} aria-label={`${p.n}. ${p.name}, ring ${p.ring}, score ${Math.round(p.score)}`}
              aria-pressed={p.key === selected} onClick={() => onSelect(p.key)} onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && onSelect(p.key)}
              onMouseEnter={() => setHover(p.key)} onMouseLeave={() => setHover(null)} onFocus={() => setHover(p.key)} onBlur={() => setHover(null)}
              className="cursor-pointer outline-none">
              <circle r={16} fill="transparent" />
              <circle r={isActive ? 12 : 10} fill={AREA_COLORS[p.area] ?? "#64748b"} stroke={p.key === selected ? "#0b1b33" : "#fff"} strokeWidth={p.key === selected ? 2.5 : 2}
                strokeDasharray={p.relation === "interest" ? "3 2" : undefined} />
              <text textAnchor="middle" dy="3.5" className="pointer-events-none fill-white text-[10px] font-bold">{p.n}</text>
            </g>
          );
        })}
      </svg>
      {active && (
        <div className="pointer-events-none absolute bottom-full left-1/2 mb-1 w-64 -translate-x-1/2 rounded-lg border border-line bg-white px-3 py-2 text-[12.5px] shadow-[var(--shadow-lift)]">
          <div className="font-medium text-ink">{active.n}. {active.name}</div>
          <div className="text-ink-3 capitalize">{active.ring} · {active.relation} · score {Math.round(active.score)}</div>
        </div>
      )}
      <div className="mt-3 grid grid-cols-1 gap-x-6 gap-y-3 text-[12.5px] sm:grid-cols-2" aria-label="Radar legend">
        {areas.map((area) => (
          <div key={area}>
            <div className="mb-1 flex items-center gap-1.5 font-semibold text-ink"><span className="size-2.5 rounded-full" style={{ background: AREA_COLORS[area] }} />{area}</div>
            <ul className="space-y-0.5">
              {placed.filter((p) => p.area === area).map((p) => (
                <li key={p.key}>
                  <button onClick={() => onSelect(p.key)} className={cn("w-full rounded px-1 text-left hover:bg-canvas", p.key === selected && "bg-brand-50 font-medium")}>
                    <span className="mr-1 font-mono text-ink-3">{p.n}.</span>{p.name} <span className="text-ink-3">· {p.ring}</span>
                  </button>
                </li>
              ))}
              {!placed.some((p) => p.area === area) && <li className="text-ink-3">No relevant technology</li>}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
