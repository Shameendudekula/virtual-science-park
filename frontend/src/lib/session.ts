export interface Session {
  token: string;
  expires_at: number;
  company: { id: number; name: string; slug: string };
}

const KEY = "vsp.session";
const ADMIN_KEY = "vsp.adminToken";

function safeGet(storage: Storage | undefined, key: string): string | null {
  try {
    return storage?.getItem(key) ?? null;
  } catch {
    return null;
  }
}

function safeSet(storage: Storage | undefined, key: string, value: string | null) {
  try {
    if (!storage) return;
    if (value === null) storage.removeItem(key);
    else storage.setItem(key, value);
  } catch {
    /* storage unavailable (private mode) — session lives in memory only */
  }
}

let memorySession: Session | null = null;
let memoryAdmin: string | null = null;
const listeners = new Set<() => void>();

export function getSession(): Session | null {
  if (memorySession) return memorySession.expires_at * 1000 > Date.now() ? memorySession : null;
  const raw = safeGet(typeof sessionStorage !== "undefined" ? sessionStorage : undefined, KEY);
  if (!raw) return null;
  try {
    const s = JSON.parse(raw) as Session;
    if (s.expires_at * 1000 <= Date.now()) return null;
    memorySession = s;
    return s;
  } catch {
    return null;
  }
}

export function setSession(s: Session | null) {
  memorySession = s;
  safeSet(typeof sessionStorage !== "undefined" ? sessionStorage : undefined, KEY, s ? JSON.stringify(s) : null);
  listeners.forEach((l) => l());
}

export function getAdminToken(): string | null {
  return memoryAdmin ?? safeGet(typeof sessionStorage !== "undefined" ? sessionStorage : undefined, ADMIN_KEY);
}

export function setAdminToken(t: string | null) {
  memoryAdmin = t;
  safeSet(typeof sessionStorage !== "undefined" ? sessionStorage : undefined, ADMIN_KEY, t);
  listeners.forEach((l) => l());
}

export function subscribe(fn: () => void) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}
