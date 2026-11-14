import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const dateFmt = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "Europe/Stockholm" });
const dateTimeFmt = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", timeZone: "Europe/Stockholm" });

export function formatDate(iso?: string | null): string {
  if (!iso) return "Not stated in source";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "Not stated in source" : dateFmt.format(d);
}

export function formatDateTime(iso?: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "—" : dateTimeFmt.format(d);
}

export function relativeDays(days?: number | null): string {
  if (days === null || days === undefined) return "";
  if (days < 0) return "closed";
  if (days === 0) return "today";
  if (days === 1) return "1 day left";
  return `${days} days left`;
}

export function titleCase(s: string): string {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}
