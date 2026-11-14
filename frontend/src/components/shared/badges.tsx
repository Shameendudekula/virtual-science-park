import type { ReactElement } from "react";
import { AlertCircle, CheckCircle2, Clock, Database, ExternalLink, Globe2, Lightbulb, MapPin, Monitor, PenLine, Quote, ShieldCheck } from "lucide-react";
import { Badge, type Tone } from "@/components/ui/primitives";
import type { ClaimType, GeoScope, Geography, Ring, Tier } from "@/types/api";
import { relativeDays } from "@/lib/utils";

const CLAIM: Record<ClaimType, { label: string; tone: Tone; icon: ReactElement; title: string }> = {
  source_stated: { label: "Source-stated", tone: "green", icon: <Quote className="size-3" />, title: "Stated in a cited public source" },
  inferred: { label: "Inferred", tone: "amber", icon: <Lightbulb className="size-3" />, title: "Rule-based inference — not a verified fact" },
  user_provided: { label: "Company-provided", tone: "violet", icon: <PenLine className="size-3" />, title: "Entered by the company in VSP" },
};

export function ClaimTypeBadge({ type }: { type: ClaimType }) {
  const c = CLAIM[type];
  return <Badge tone={c.tone} icon={c.icon} title={c.title}>{c.label}</Badge>;
}

export function ProvenanceBadge({ provenance }: { provenance: string }) {
  if (provenance === "live") return <Badge tone="green" icon={<Database className="size-3" />} title="Collected live from the source API">Live data</Badge>;
  if (provenance === "snapshot") return <Badge tone="neutral" icon={<Clock className="size-3" />} title="Previously collected from the source; not live">Collected snapshot</Badge>;
  if (provenance === "user") return <Badge tone="violet">User input</Badge>;
  return <Badge tone="amber" title="Demonstration data">Demo data</Badge>;
}

export function VerificationBadge({ status }: { status: string }) {
  if (status === "verified") return <Badge tone="green" icon={<ShieldCheck className="size-3" />} title="Excerpt was found verbatim at the URL">Excerpt verified</Badge>;
  if (status === "not_found") return <Badge tone="red" icon={<AlertCircle className="size-3" />} title="Excerpt no longer found — source may have changed">Excerpt not found</Badge>;
  if (status === "fetch_failed") return <Badge tone="amber">Page unreachable</Badge>;
  return <Badge tone="neutral">Not checked</Badge>;
}

const TIER: Record<Tier, { label: string; tone: Tone }> = {
  high: { label: "High priority", tone: "red" },
  medium: { label: "Medium priority", tone: "amber" },
  later: { label: "Explore later", tone: "neutral" },
};
export function TierBadge({ tier }: { tier: Tier }) {
  return <Badge tone={TIER[tier].tone}>{TIER[tier].label}</Badge>;
}

export const RING_LABEL: Record<Ring, string> = { adopt: "Adopt", trial: "Trial", assess: "Assess", monitor: "Monitor" };
export function RingBadge({ ring }: { ring: Ring }) {
  const tone: Record<Ring, Tone> = { adopt: "navy", trial: "brand", assess: "teal", monitor: "neutral" };
  return <Badge tone={tone[ring]}>{RING_LABEL[ring]}</Badge>;
}

export function BandBadge({ band, score }: { band: string; score?: number }) {
  const tone: Record<string, Tone> = { strong: "brand", moderate: "teal", weak: "neutral", low: "neutral" };
  return <Badge tone={tone[band] ?? "neutral"} title="Heuristic relevance score — not a probability">{score !== undefined ? `${score} · ` : ""}{band}</Badge>;
}

export function DeadlineBadge({ deadline, days, status }: { deadline?: string | null; days?: number | null; status?: string }) {
  if (!deadline) return <Badge tone="neutral" icon={<Clock className="size-3" />}>{status === "placeholder_rejected" ? "Deadline not stated (placeholder rejected)" : "Deadline not stated in source"}</Badge>;
  if (days !== null && days !== undefined && days < 0) return <Badge tone="neutral">Closed</Badge>;
  const urgent = days !== null && days !== undefined && days <= 21;
  return (
    <Badge tone={urgent ? "red" : "neutral"} icon={urgent ? <AlertCircle className="size-3" /> : <Clock className="size-3" />}>
      {new Date(deadline).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "Europe/Stockholm" })}
      {days !== null && days !== undefined ? ` · ${relativeDays(days)}` : ""}
    </Badge>
  );
}

const GEO_LABEL: Record<GeoScope, string> = { karlskrona: "Karlskrona", blekinge: "Blekinge", sweden: "Sweden", europe: "Europe", international: "International", online: "Online" };

export function LocationBadges({ scopes, inferred, max = 2 }: { scopes: GeoScope[]; inferred?: boolean; max?: number }) {
  if (!scopes?.length) return <Badge tone="neutral" icon={<MapPin className="size-3" />}>Location not stated</Badge>;
  // Show the most specific scopes first (Karlskrona before Blekinge before Sweden).
  const shown = scopes.filter((s) => s !== "online").slice(0, max);
  return (
    <span className="inline-flex flex-wrap gap-1">
      {scopes.includes("online") && <Badge tone="teal" icon={<Monitor className="size-3" />}>Online</Badge>}
      {shown.map((s) => (
        <Badge key={s} tone={s === "karlskrona" || s === "blekinge" ? "brand" : "neutral"} icon={s === "europe" || s === "international" ? <Globe2 className="size-3" /> : <MapPin className="size-3" />}
          title={inferred ? "Location inferred (see basis)" : "Location stated in source"}>
          {GEO_LABEL[s]}{inferred ? " · inferred" : ""}
        </Badge>
      ))}
    </span>
  );
}

export function RegionalNote({ geo }: { geo?: Geography | null }) {
  if (!geo) return null;
  return (
    <div className="flex items-start gap-2 rounded-lg bg-brand-50/60 px-3 py-2 text-[12.5px] text-ink-2">
      <MapPin className="mt-0.5 size-3.5 shrink-0 text-brand" aria-hidden />
      <div>
        <span className="font-medium text-ink">{geo.relevance_label}:</span> {geo.explanation}
        {geo.basis && <div className="mt-0.5 text-ink-3">Basis: {geo.basis}{geo.format_basis && geo.format !== "not_applicable" ? ` Format: ${geo.format_basis}` : ""}</div>}
      </div>
    </div>
  );
}

export function SourceLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 font-medium text-brand hover:underline">
      {children}
      <ExternalLink className="size-3.5" aria-hidden />
      <span className="sr-only">(opens in a new tab)</span>
    </a>
  );
}

export function StatusPill({ status }: { status: string }) {
  const map: Record<string, { tone: Tone; label: string; icon?: ReactElement }> = {
    healthy: { tone: "green", label: "Healthy", icon: <CheckCircle2 className="size-3" /> },
    snapshot_only: { tone: "neutral", label: "Snapshot only", icon: <Clock className="size-3" /> },
    degraded: { tone: "amber", label: "Degraded", icon: <AlertCircle className="size-3" /> },
    failing: { tone: "red", label: "Failing", icon: <AlertCircle className="size-3" /> },
    never_run: { tone: "neutral", label: "Never run" },
    disabled: { tone: "neutral", label: "Not activated" },
    not_applicable: { tone: "neutral", label: "Not collected" },
    success: { tone: "green", label: "Success", icon: <CheckCircle2 className="size-3" /> },
    partial: { tone: "amber", label: "Partial" },
    failed: { tone: "red", label: "Failed", icon: <AlertCircle className="size-3" /> },
  };
  const m = map[status] ?? { tone: "neutral" as Tone, label: status };
  return <Badge tone={m.tone} icon={m.icon}>{m.label}</Badge>;
}
