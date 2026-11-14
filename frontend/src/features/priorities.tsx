import { AnimatePresence, motion } from "framer-motion";
import { ArrowDown, ArrowUp, Minus, Plus, SlidersHorizontal, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Button, Card, CardBody, CardHeader } from "@/components/ui/primitives";
import { TierBadge } from "@/components/shared/badges";
import { READ_ONLY_HINT, useReadOnly } from "@/app/workspace";
import { useSetPriorities } from "@/services/queries";
import type { Priority, RankingChange } from "@/types/api";
import { cn } from "@/lib/utils";

const LEVELS = [
  { v: 0, label: "Off" },
  { v: 1, label: "Normal" },
  { v: 2, label: "Important" },
  { v: 3, label: "Top" },
];

export function PriorityEditor({ companyId, priorities, compact = false, onChanges }: {
  companyId: number; priorities: Priority[]; compact?: boolean; onChanges?: (c: RankingChange[]) => void;
}) {
  const [draft, setDraft] = useState<Record<string, number>>({});
  const [changes, setChanges] = useState<RankingChange[] | null>(null);
  const m = useSetPriorities(companyId);
  const readOnly = useReadOnly();
  useEffect(() => setDraft(Object.fromEntries(priorities.map((p) => [p.key, p.weight]))), [priorities]);
  const dirty = priorities.some((p) => draft[p.key] !== undefined && draft[p.key] !== p.weight);

  const apply = async () => {
    const res = await m.mutateAsync(draft);
    setChanges(res.ranking_changes);
    onChanges?.(res.ranking_changes);
  };

  return (
    <Card>
      <CardHeader icon={<SlidersHorizontal className="size-4" />} title="Your priorities"
        subtitle="Tell VSP what matters now. Rankings are recalculated with transparent rules." />
      <CardBody className="space-y-3">
        <ul className={cn("grid gap-3", compact ? "grid-cols-1" : "md:grid-cols-2")}>
          {priorities.map((p) => (
            <li key={p.key} className="rounded-xl border border-line p-3">
              <div className="text-[13.5px] font-medium text-ink">{p.label}</div>
              {!compact && <div className="text-[12px] text-ink-3">{p.description}</div>}
              <div role="radiogroup" aria-label={p.label} className="mt-2 grid grid-cols-4 gap-1 rounded-lg bg-slate-100 p-1">
                {LEVELS.map((l) => (
                  <button key={l.v} role="radio" aria-checked={draft[p.key] === l.v} onClick={() => setDraft((d) => ({ ...d, [p.key]: l.v }))}
                    className={cn("rounded-md py-1 text-[12px] font-medium transition", draft[p.key] === l.v ? "bg-white text-ink shadow-sm" : "text-ink-3 hover:text-ink")}>
                    {l.label}
                  </button>
                ))}
              </div>
            </li>
          ))}
        </ul>
        <div className="flex flex-wrap items-center gap-3">
          <Button onClick={apply} disabled={!dirty || readOnly} loading={m.isPending} title={readOnly ? READ_ONLY_HINT : undefined}>Update recommendations</Button>
          {readOnly && <span className="text-[12.5px] text-ink-3">{READ_ONLY_HINT}</span>}
          {m.isError && <span role="alert" className="text-[13px] text-critical">{(m.error as Error).message}</span>}
          {!readOnly && !dirty && !changes && <span className="text-[12.5px] text-ink-3">Change a priority to see how the ranking responds.</span>}
        </div>
        <AnimatePresence>{changes && <RankingDiff changes={changes} />}</AnimatePresence>
      </CardBody>
    </Card>
  );
}

export function RankingDiff({ changes }: { changes: RankingChange[] }) {
  const shown = changes.slice(0, 8);
  return (
    <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}
      className="overflow-hidden rounded-xl border border-brand-100 bg-brand-50/50" aria-live="polite">
      <div className="px-4 pt-3 text-[13px] font-semibold text-ink">
        {changes.length ? `${changes.length} recommendation${changes.length === 1 ? "" : "s"} moved` : "No ranking changes — your priorities did not affect the order."}
      </div>
      {!!shown.length && (
        <ul className="divide-y divide-brand-100 px-4 pb-2">
          {shown.map((c) => (
            <li key={c.fingerprint} className="flex items-center gap-3 py-2 text-[13px]">
              <ChangeIcon change={c.change} />
              <span className="min-w-0 flex-1 truncate text-ink">{c.title}</span>
              <span className="whitespace-nowrap font-mono text-[12px] tabular-nums text-ink-2">
                {c.before ? `#${c.before.position}` : "new"} → {c.after ? `#${c.after.position}` : "removed"}
              </span>
              {c.after && c.before && c.after.tier !== c.before.tier && <TierBadge tier={c.after.tier} />}
            </li>
          ))}
        </ul>
      )}
    </motion.div>
  );
}

function ChangeIcon({ change }: { change: RankingChange["change"] }) {
  const map = {
    up: { icon: <ArrowUp className="size-3.5" />, cls: "bg-emerald-100 text-emerald-700", label: "Moved up" },
    down: { icon: <ArrowDown className="size-3.5" />, cls: "bg-slate-200 text-ink-2", label: "Moved down" },
    new: { icon: <Plus className="size-3.5" />, cls: "bg-brand-100 text-brand-600", label: "New" },
    removed: { icon: <Trash2 className="size-3.5" />, cls: "bg-slate-200 text-ink-3", label: "Removed" },
    tier: { icon: <Minus className="size-3.5" />, cls: "bg-amber-100 text-amber-800", label: "Tier changed" },
  }[change];
  return <span title={map.label} className={cn("flex size-6 shrink-0 items-center justify-center rounded-full", map.cls)}>{map.icon}<span className="sr-only">{map.label}</span></span>;
}
