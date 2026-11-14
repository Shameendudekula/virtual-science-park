import { getAdminToken, getSession, setSession } from "./session";

export class ApiError extends Error {
  status: number;
  code: string;
  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

const BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") ?? "";

export async function api<T>(path: string, init: RequestInit & { admin?: boolean } = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const session = getSession();
  if (session) headers.set("Authorization", `Bearer ${session.token}`);
  if (init.admin) {
    const admin = getAdminToken();
    if (admin) headers.set("X-Admin-Token", admin);
  }
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, "network_error", "The API could not be reached. Check that the backend is running.");
  }
  if (!res.ok) {
    let code = "error";
    let message = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      code = body?.error?.code ?? code;
      message = body?.error?.message ?? message;
    } catch {
      /* non-JSON error */
    }
    if (res.status === 401 && session) setSession(null);
    throw new ApiError(res.status, code, message);
  }
  const type = res.headers.get("content-type") ?? "";
  if (type.includes("application/json")) return (await res.json()) as T;
  return (await res.blob()) as unknown as T;
}

export const post = <T>(path: string, body?: unknown, opts: { admin?: boolean } = {}) =>
  api<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body), ...opts });
export const put = <T>(path: string, body: unknown) => api<T>(path, { method: "PUT", body: JSON.stringify(body) });
export const patch = <T>(path: string, body: unknown) => api<T>(path, { method: "PATCH", body: JSON.stringify(body) });
