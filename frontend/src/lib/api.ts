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

type AdminOptions = {
  /** Send the admin token (if one is stored) with this request. */
  admin?: boolean;
  /** The endpoint is authorised by the admin token alone and never evaluates the company session (collectors, demo
   * reset), so its 401 says nothing about that session: keep the session. Implies `admin`. */
  adminOnly?: boolean;
};

export async function api<T>(path: string, init: RequestInit & AdminOptions = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const session = getSession();
  if (session) headers.set("Authorization", `Bearer ${session.token}`);
  if (init.admin || init.adminOnly) {
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
    // An expired or invalid company session ends the session; a refused admin token on an admin-only endpoint does not.
    if (res.status === 401 && session && !init.adminOnly) setSession(null);
    throw new ApiError(res.status, code, message);
  }
  const type = res.headers.get("content-type") ?? "";
  if (type.includes("application/json")) return (await res.json()) as T;
  return (await res.blob()) as unknown as T;
}

/** A short, user-safe message for a failed action. Client-error and network messages are fixed text from the API
 * (no internals); anything else gets a generic message, so server details are never shown. */
export function actionErrorMessage(error: unknown): string {
  if (error instanceof ApiError && (error.status === 0 || (error.status >= 400 && error.status < 500)) && error.message) return error.message;
  return "Something went wrong. Please try again.";
}

export const post = <T>(path: string, body?: unknown, opts: AdminOptions = {}) =>
  api<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body), ...opts });
export const put = <T>(path: string, body: unknown) => api<T>(path, { method: "PUT", body: JSON.stringify(body) });
export const patch = <T>(path: string, body: unknown) => api<T>(path, { method: "PATCH", body: JSON.stringify(body) });
