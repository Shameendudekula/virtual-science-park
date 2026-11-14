import { CheckCircle2, Database, KeyRound, MapPin, Play, RefreshCw, RotateCcw, Search, Users } from "lucide-react";
import { useMemo, useState, useSyncExternalStore } from "react";
import { Badge, Button, Card, CardBody, CardHeader, ErrorState, LoadingBlock, PageHeader, inputClass } from "@/components/ui/primitives";
import { SourceLink, StatusPill } from "@/components/shared/badges";
import { getAdminToken, setAdminToken, subscribe } from "@/lib/session";
import { useAdminStatus, useDemoReset, useHealth, useMembers, useRunCollector, useSourceHealth } from "@/services/queries";
import { actionErrorMessage } from "@/lib/api";
import { formatDate, formatDateTime } from "@/lib/utils";

const useAdminToken = () => useSyncExternalStore(subscribe, getAdminToken, getAdminToken);

// ------------------------------------------------------------------------------------------- Data sources
export function DataSources() {
  const q = useSourceHealth();
  const run = useRunCollector();
  const token = useAdminToken();
  const [last, setLast] = useState<string | null>(null);
  if (q.isLoading) return <LoadingBlock rows={5} />;
  if (q.isError) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  const { sources, runs } = q.data!;
  const trigger = async (key: string, mode: "live" | "snapshot") => {
    setLast(null);
    try {
      const r = await run.mutateAsync({ key, mode });
      setLast(`${key}: ${r.status} — ${r.created} new, ${r.updated} updated, ${r.unchanged} unchanged, ${r.rejected} rejected. ${r.message ?? ""}`);
    } catch (e) {
      setLast(`${key}: ${(e as Error).message}`);
    }
  };
  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Data provenance" title="Data Sources" description="Every record is traceable to a source with a retrieval date. Snapshot data is never labelled as live." />
      {!token && <Card className="flex items-center gap-3 p-4 text-[13px] text-ink-2"><KeyRound className="size-4 text-brand" />Running collectors requires the admin token. Add it under Settings (stored only for this browser session).</Card>}
      {last && <Card role="status" className="p-4 text-[13px] text-ink">{last}</Card>}
      <div className="grid gap-4 lg:grid-cols-2">
        {sources.map((s) => (
          <Card key={s.key}>
            <CardHeader icon={<Database className="size-4" />} title={s.name} subtitle={`${s.publisher} · ${s.source_type.replace("_", " ")}`} action={<StatusPill status={s.enabled ? s.health.status : "disabled"} />} />
            <CardBody className="space-y-3 text-[13px]">
              <p className="text-ink-2">{s.description}</p>
              <dl className="grid grid-cols-2 gap-2 text-[12.5px]">
                <div><dt className="text-ink-3">Records</dt><dd className="font-medium text-ink">{s.health.record_count}</dd></div>
                <div><dt className="text-ink-3">Data mode</dt><dd className="font-medium capitalize text-ink">{s.health.data_mode ?? "—"}</dd></div>
                <div><dt className="text-ink-3">Last successful live collection</dt><dd className="font-medium text-ink">{formatDateTime(s.health.last_success_at)}</dd></div>
                <div><dt className="text-ink-3">Last attempt</dt><dd className="font-medium text-ink">{formatDateTime(s.health.last_attempt_at)}</dd></div>
              </dl>
              {s.health.last_error && <p className="rounded-lg bg-red-50 p-2 text-[12.5px] text-red-800">Last error: {s.health.last_error}</p>}
              <p className="text-[12px] text-ink-3">Licence & reuse: {s.license_note}</p>
              {!s.enabled && s.disabled_reason && <p className="text-[12px] text-ink-3">{s.disabled_reason}</p>}
              <div className="flex flex-wrap items-center gap-2">
                {s.enabled && s.collectable && (
                  <>
                    <Button size="sm" icon={<Play className="size-3.5" />} disabled={!token} loading={run.isPending && run.variables?.key === s.key && run.variables.mode === "live"} onClick={() => trigger(s.key, "live")}>Collect live</Button>
                    {s.key !== "company_websites" && <Button size="sm" variant="outline" icon={<RefreshCw className="size-3.5" />} disabled={!token} onClick={() => trigger(s.key, "snapshot")}>Reload snapshot</Button>}
                  </>
                )}
                {s.base_url && <SourceLink href={s.base_url}>Source</SourceLink>}
              </div>
            </CardBody>
          </Card>
        ))}
      </div>
      <Card>
        <CardHeader title="Collection runs" subtitle="A failed run never deletes or changes existing records." />
        <CardBody className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-[13px]">
            <thead className="text-[12px] text-ink-3"><tr><th className="pb-2 font-medium">Source</th><th className="pb-2 font-medium">Mode</th><th className="pb-2 font-medium">Status</th><th className="pb-2 font-medium">Started</th><th className="pb-2 font-medium">Fetched</th><th className="pb-2 font-medium">New / updated / unchanged</th><th className="pb-2 font-medium">Rejected</th></tr></thead>
            <tbody className="divide-y divide-line">
              {runs.map((r) => (
                <tr key={r.id}>
                  <td className="py-2 font-medium text-ink">{r.source_key}</td><td className="py-2 capitalize">{r.mode}</td><td className="py-2"><StatusPill status={r.status} /></td>
                  <td className="py-2">{formatDateTime(r.started_at)}</td><td className="py-2 tabular-nums">{r.fetched}</td>
                  <td className="py-2 tabular-nums">{r.created} / {r.updated} / {r.unchanged}</td>
                  <td className="py-2" title={JSON.stringify(r.rejection_reasons)}>{r.rejected}{r.rejected > 0 && <span className="text-ink-3"> ({Object.entries(r.rejection_reasons).map(([k, v]) => `${k.replace(/_/g, " ")}: ${v}`).join(", ")})</span>}{r.error && <div className="text-red-700">{r.error}</div>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardBody>
      </Card>
    </div>
  );
}

// ------------------------------------------------------------------------------------------- Members
export function Members() {
  const q = useMembers();
  const [filter, setFilter] = useState("");
  const items = useMemo(() => (q.data?.items ?? []).filter((m) => m.name.toLowerCase().includes(filter.toLowerCase())), [q.data, filter]);
  if (q.isLoading) return <LoadingBlock rows={5} />;
  if (q.isError) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  const d = q.data!;
  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Ecosystem" title="Blue Science Park member directory" description={d.note}
        actions={<><Badge tone="green">{d.verified_members} verified members</Badge><Badge tone="brand">{d.profile_levels.full} full profiles</Badge><Badge tone="teal">{d.profile_levels.partial} partial</Badge><Badge tone="neutral">{d.profile_levels.directory} directory only</Badge></>} />
      <label className="relative block max-w-md"><span className="sr-only">Filter members</span><Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-ink-3" /><input value={filter} onChange={(e) => setFilter(e.target.value)} className={`${inputClass} pl-9`} placeholder="Filter by name" /></label>
      <Card>
        <CardBody className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-[13px]">
            <thead className="text-[12px] text-ink-3"><tr><th className="pb-2 font-medium">Organisation</th><th className="pb-2 font-medium">VSP profile</th><th className="pb-2 font-medium">Location</th><th className="pb-2 font-medium">Membership evidence</th></tr></thead>
            <tbody className="divide-y divide-line">
              {items.map((m) => (
                <tr key={m.id}>
                  <td className="py-2.5 font-medium text-ink">{m.name}{m.is_demo_company && <Badge tone="brand" className="ml-2">Demo company</Badge>}</td>
                  <td className="py-2.5">{m.profile_level === "full" ? <Badge tone="brand">Full profile</Badge> : m.profile_level === "partial" ? <Badge tone="teal">Partial profile</Badge> : <Badge tone="neutral" title="No capabilities inferred">Directory only</Badge>}</td>
                  <td className="py-2.5 text-ink-2"><MapPin className="mr-1 inline size-3.5 text-ink-3" />{m.location.label}</td>
                  <td className="py-2.5">{m.membership_url ? <><SourceLink href={m.membership_url}>Member page</SourceLink><div className="text-[11.5px] text-ink-3">{m.membership_provenance} · retrieved {formatDate(m.membership_retrieved_at)}</div></> : <span className="text-ink-3">Unverified</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardBody>
      </Card>
    </div>
  );
}

// ------------------------------------------------------------------------------------------- Settings
export function SettingsPage() {
  const health = useHealth();
  const token = useAdminToken();
  const [value, setValue] = useState("");
  const reset = useDemoReset();
  // The reset is offered only when the API has confirmed that the stored admin token is valid (never from DEMO_MODE).
  const admin = useAdminStatus(!!token);
  const serverHasAdmin = health.data?.admin_actions_enabled !== false;
  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Workspace" title="Settings" />
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader icon={<KeyRound className="size-4" />} title="Admin token" subtitle="Required to run collectors and to reset the demo. Kept in this browser session only; never sent anywhere except the VSP API." />
          <CardBody className="space-y-3">
            {token ? <div className="flex items-center gap-2 text-[13px] text-ink"><CheckCircle2 className="size-4 text-good" />Admin token set for this session.<Button size="sm" variant="ghost" onClick={() => setAdminToken(null)}>Remove</Button></div> : (
              <form onSubmit={(e) => { e.preventDefault(); if (value) setAdminToken(value); setValue(""); }} className="flex gap-2">
                <input type="password" value={value} onChange={(e) => setValue(e.target.value)} className={inputClass} placeholder="ADMIN_TOKEN from .env" aria-label="Admin token" autoComplete="off" />
                <Button type="submit">Save</Button>
              </form>
            )}
            {health.data && !health.data.admin_actions_enabled && <p className="text-[12.5px] text-ink-3">The server has no ADMIN_TOKEN configured, so collectors and the demo reset are disabled.</p>}
          </CardBody>
        </Card>
        <Card>
          <CardHeader icon={<RotateCcw className="size-4" />} title="Demo reset" subtitle="Admin only. Removes profile edits, reviews, priorities and saved items for all workspaces. Collected source data is kept." />
          <CardBody className="space-y-3">
            {!serverHasAdmin ? <p className="text-[13px] text-ink-3">Not available: the server has no admin token configured.</p>
              : !token ? <p className="text-[13px] text-ink-3">The reset requires the admin token. Add it in the Admin token card to enable it.</p>
                : admin.isLoading ? <p className="text-[13px] text-ink-3">Checking the admin token…</p>
                  : admin.data?.is_admin ? (
                    <Button variant="outline" loading={reset.isPending} onClick={() => reset.mutate()} icon={<RotateCcw className="size-4" />}>Reset demo workspace</Button>
                  ) : <p role="alert" className="text-[13px] text-critical">The saved admin token was not accepted. Remove it and enter the correct token.</p>}
            {reset.isSuccess && <p role="status" className="text-[13px] text-good">Workspace reset to a clean state.</p>}
            {reset.isError && <p role="alert" className="text-[13px] text-critical">Reset failed. {actionErrorMessage(reset.error)}</p>}
          </CardBody>
        </Card>
        <Card className="lg:col-span-2">
          <CardHeader icon={<Users className="size-4" />} title="System" />
          <CardBody className="grid gap-3 text-[13px] sm:grid-cols-4">
            <div><div className="text-ink-3">API</div><div className="font-medium text-ink">{health.data?.status ?? "…"} · v{health.data?.version}</div></div>
            <div><div className="text-ink-3">Demo mode</div><div className="font-medium text-ink">{health.data?.demo_mode ? "On (password-free, read-only demo login)" : "Off"}</div></div>
            <div><div className="text-ink-3">LLM</div><div className="font-medium text-ink">{health.data?.llm.enabled ? `Enabled (${health.data.llm.provider})` : "Not configured — deterministic only"}</div></div>
            <div><div className="text-ink-3">Reference date</div><div className="font-medium text-ink">{health.data?.today}</div></div>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
