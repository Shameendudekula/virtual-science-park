import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const dateFmt = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "Europe/Stockholm" });
const dateTimeFmt = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", timeZone: "Europe/Stockholm" });

/** Parses an ISO date; returns null for missing or unreadable values instead of an "Invalid Date". */
export function parseDate(iso?: string | null): Date | null {
  if (!iso) return null;
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? null : d;
}

export function formatDate(iso?: string | null): string {
  const d = parseDate(iso);
  return d ? dateFmt.format(d) : "Not stated in source";
}

export function formatDateTime(iso?: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "—" : dateTimeFmt.format(d);
}

export function relativeDays(days?: number | null): string {
  if (days === null || days === undefined) return "";
  if (days < 0) return "closed";
  if (days === 0) return "closes today";
  if (days === 1) return "1 day left";
  return `${days} days left`;
}

export type DeadlineGroup = "upcoming" | "closed" | "undated";

/** Classifies an application deadline. `days` comes from the API (reference-date aware) and wins over the browser clock. */
export function deadlineGroup(deadline?: string | null, days?: number | null): DeadlineGroup {
  const d = parseDate(deadline);
  if (!d) return "undated";
  if (days !== null && days !== undefined) return days < 0 ? "closed" : "upcoming";
  return d.getTime() < Date.now() ? "closed" : "upcoming";
}

const GROUP_ORDER: Record<DeadlineGroup, number> = { upcoming: 0, closed: 1, undated: 2 };

/**
 * Returns a NEW array (input untouched): upcoming deadlines nearest first, then closed (most recently closed first),
 * then items without a usable deadline. Ties keep their original order.
 */
export function sortByDeadline<T extends { deadline_at: string | null; timeliness: { days_left: number | null } }>(items: readonly T[]): T[] {
  return items
    .map((item, index) => ({ item, index, group: deadlineGroup(item.deadline_at, item.timeliness.days_left), t: parseDate(item.deadline_at)?.getTime() ?? 0 }))
    .sort((a, b) => GROUP_ORDER[a.group] - GROUP_ORDER[b.group] || (a.group === "closed" ? b.t - a.t : a.t - b.t) || a.index - b.index)
    .map((x) => x.item);
}

export function titleCase(s: string): string {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}
