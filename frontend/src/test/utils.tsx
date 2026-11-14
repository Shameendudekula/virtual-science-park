import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { vi } from "vitest";
import { WorkspaceGate } from "@/app/workspace";
import { setSession } from "@/lib/session";

type Handler = (url: string, init?: RequestInit) => { status?: number; body: unknown } | undefined;

export function mockFetch(handler: Handler) {
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === "string" ? input : input.toString();
    const r = handler(url, init) ?? { status: 404, body: { error: { code: "not_found", message: `No mock for ${url}` } } };
    return new Response(JSON.stringify(r.body), { status: r.status ?? 200, headers: { "Content-Type": "application/json" } });
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}

export const HEALTH = { status: "ok", database: "ok", version: "1.0.0", demo_mode: true, llm: { enabled: false, provider: null }, admin_actions_enabled: true, today: "2026-11-13", counts: {} };

export function signIn(id = 6, name = "Ocean Harvesting") {
  setSession({ token: "t.sig", expires_at: Math.floor(Date.now() / 1000) + 3600, company: { id, name, slug: "ocean-harvesting" } });
}

export function renderWorkspace(path: string, route: string, element: ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes><Route path={route} element={<WorkspaceGate>{element}</WorkspaceGate>} /></Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

export function renderPlain(ui: ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}><MemoryRouter>{ui}</MemoryRouter></QueryClientProvider>);
}
