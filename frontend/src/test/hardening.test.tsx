import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { WorkspaceGate, useWorkspace } from "@/app/workspace";
import { getSession, setSession } from "@/lib/session";
import Focus from "@/pages/Focus";
import Login from "@/pages/Login";
import Recommendations from "@/pages/Recommendations";
import { HEALTH, mockFetch, renderWorkspace } from "./utils";

const EXP = () => Math.floor(Date.now() / 1000) + 3600;
const OCEAN = { id: 6, name: "Ocean Harvesting", slug: "ocean-harvesting" };
const ROXTEC = { id: 7, name: "Roxtec", slug: "roxtec" };
const passwordSession = () => setSession({ token: "pw.sig", expires_at: EXP(), company: OCEAN, read_only: false });
const demoSession = () => setSession({ token: "demo.sig", expires_at: EXP(), company: OCEAN, read_only: true });

afterEach(() => {
  vi.unstubAllGlobals();
  act(() => setSession(null));
});

// ------------------------------------------------------------------------------------------- recommendation action errors
const focusBody = (status: string) => ({
  company: { id: 6, name: "Ocean Harvesting", location: null },
  time_saved: { opportunities_screened: 206, sources: ["Vinnova"], relevant: 6, message: "VSP screened 206 records." },
  top_three: [{ id: 1, title: "Develop a research proposal: Industrial flexible energy control", tier: "high", kind: "research_proposal", status, why: ["Shared technology areas"], next_step: "Read the call text.", source: null, geography: null }],
  deadlines: [], new_opportunities: [], local_events: [], regional_partners: [], wider_partners: [], technologies: [], saved: [], saved_count: 0,
  priorities: [{ key: "find_funding", label: "Find new funding", description: "Grants", weight: 1 }], freshness: "Collected snapshot",
});
const error = (status: number, message: string) => ({ status, body: { error: { code: status === 403 ? "forbidden" : "internal_error", message } } });

describe("recommendation action errors", () => {
  it("Focus: shows the API's message when saving fails, and keeps the button usable", async () => {
    passwordSession();
    mockFetch((url, init) => {
      if (url.includes("/api/health")) return { body: HEALTH };
      if (url.includes("/focus")) return { body: focusBody("open") };
      if (url.includes("/api/recommendations/1/save") && init?.method === "POST") return error(403, "Your session belongs to a different company workspace.");
      return undefined;
    });
    renderWorkspace("/app/6/focus", "/app/:companyId/focus", <Focus />);
    fireEvent.click(await screen.findByRole("button", { name: "Save" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Could not update this recommendation. Your session belongs to a different company workspace.");
    expect(screen.getByRole("button", { name: "Save" })).toBeEnabled();
  });

  it("Focus: never shows server internals for a 500", async () => {
    passwordSession();
    mockFetch((url, init) => {
      if (url.includes("/api/health")) return { body: HEALTH };
      if (url.includes("/focus")) return { body: focusBody("open") };
      if (init?.method === "POST") return error(500, "Traceback (most recent call last): psycopg.OperationalError at 10.0.0.5");
      return undefined;
    });
    renderWorkspace("/app/6/focus", "/app/:companyId/focus", <Focus />);
    fireEvent.click(await screen.findByRole("button", { name: "Save" }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Something went wrong. Please try again.");
    expect(alert).not.toHaveTextContent(/Traceback|psycopg|10\.0\.0\.5/);
  });

  it("Focus: a successful save still updates the card and shows no error", async () => {
    passwordSession();
    let saved = false;
    mockFetch((url, init) => {
      if (url.includes("/api/health")) return { body: HEALTH };
      if (url.includes("/api/recommendations/1/save") && init?.method === "POST") { saved = true; return { body: { id: 1, status: "saved" } }; }
      if (url.includes("/focus")) return { body: focusBody(saved ? "saved" : "open") };
      return undefined;
    });
    renderWorkspace("/app/6/focus", "/app/:companyId/focus", <Focus />);
    fireEvent.click(await screen.findByRole("button", { name: "Save" }));
    expect(await screen.findByRole("button", { name: "Saved" })).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("Recommendation Centre: shows the error on the card whose action failed", async () => {
    passwordSession();
    const rec = (id: number, title: string) => ({
      id, company_id: 6, fingerprint: `f${id}`, kind: "apply_funding", title, priority_tier: "high", rank_score: 60, rank_position: id, status: "open",
      status_changed_at: null, related_opportunity_id: null, related_company_id: null, related_technology_id: null, computed_at: "2026-11-13T12:00:00Z",
      detail: { what: "x", why: ["Shared technology areas"], capabilities: [], business_value: "x", evidence_ids: [], claim_ids: [], uncertainties: [], next_step: "Read the call.", criteria: [], tier_rule: "x" },
    });
    mockFetch((url, init) => {
      if (url.includes("/api/health")) return { body: HEALTH };
      if (url.includes("/api/recommendations/2/explore") && init?.method === "POST") return error(403, "This is a read-only demo session. Sign in with the company's username and password to change profiles, priorities or saved items.");
      if (url.includes("/recommendations")) return { body: { items: [rec(1, "First action"), rec(2, "Second action")], summary: { headline: "h", bullets: [], generated_by: "template", as_of: "2026-11-13" }, method: { ranking: "r", tiers: { high: "h", medium: "m", later: "l" } } } };
      return undefined;
    });
    renderWorkspace("/app/6/recommendations", "/app/:companyId/recommendations", <Recommendations />);
    await screen.findByText("Second action");
    fireEvent.click(screen.getAllByRole("button", { name: "Mark explored" })[1]);
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/Could not update this recommendation\. This is a read-only demo session/);
    expect(alert.closest("li")).toHaveTextContent("Second action");
    expect(screen.getAllByRole("alert")).toHaveLength(1);
  });
});

// ------------------------------------------------------------------------------------------- workspace switching
function Child() {
  const { companyId } = useWorkspace();
  return <p>Workspace {companyId}</p>;
}

function renderApp(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/app/:companyId/*" element={<WorkspaceGate><Child /></WorkspaceGate>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function backend() {
  return mockFetch((url) => {
    if (url.includes("/api/health")) return { body: HEALTH };
    if (url.includes("/api/auth/demo-login")) return { body: { token: "demo7.sig", expires_at: EXP(), read_only: true, company: ROXTEC } };
    if (url.includes("/api/companies/7")) return { body: { ...ROXTEC, tagline: null, website: null, profile_level: "full", organisation_type: "company", membership_status: "verified", is_demo_company: true } };
    if (url.includes("/api/companies")) return { body: { items: [{ ...OCEAN, is_demo_company: true }, { ...ROXTEC, is_demo_company: true }], total: 2, page: 1, page_size: 100 } };
    return undefined;
  });
}
const demoLoginCalls = (f: ReturnType<typeof backend>) => f.mock.calls.filter(([u]) => String(u).includes("/api/auth/demo-login")).length;

describe("switching workspaces in demo mode", () => {
  it("asks before replacing a signed-in session, and 'Stay' keeps it", async () => {
    passwordSession();
    const fetchMock = backend();
    renderApp("/app/7/focus");
    expect(await screen.findByRole("alertdialog", { name: "Leave your signed-in workspace?" })).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Sign in to Roxtec" })).toBeInTheDocument();
    expect(demoLoginCalls(fetchMock)).toBe(0);
    fireEvent.click(screen.getByRole("button", { name: "Stay in Ocean Harvesting" }));
    expect(await screen.findByText("Workspace 6")).toBeInTheDocument();
    expect(getSession()).toMatchObject({ token: "pw.sig", read_only: false });
    expect(demoLoginCalls(fetchMock)).toBe(0);
  });

  it("replaces the session only after the user chooses the read-only demo", async () => {
    passwordSession();
    const fetchMock = backend();
    renderApp("/app/7/focus");
    fireEvent.click(await screen.findByRole("button", { name: "Open read-only demo" }));
    expect(await screen.findByText("Workspace 7")).toBeInTheDocument();
    expect(demoLoginCalls(fetchMock)).toBe(1);
    expect(getSession()).toMatchObject({ company: { id: 7 }, read_only: true });
  });

  it("offers signing in to the other company instead", async () => {
    passwordSession();
    backend();
    renderApp("/app/7/focus");
    fireEvent.click(await screen.findByRole("button", { name: "Sign in to Roxtec" }));
    expect(await screen.findByRole("heading", { name: "Sign in to your company workspace" })).toBeInTheDocument();
    expect(getSession()).toMatchObject({ token: "pw.sig" });
  });

  it("does not ask when the current session is already a read-only demo (unchanged behaviour)", async () => {
    demoSession();
    const fetchMock = backend();
    renderApp("/app/7/focus");
    expect(await screen.findByText("Workspace 7")).toBeInTheDocument();
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    expect(demoLoginCalls(fetchMock)).toBe(1);
  });

  it("the Login page's demo buttons also go through the confirmation", async () => {
    passwordSession();
    const fetchMock = backend();
    renderApp("/login");
    fireEvent.click(await screen.findByRole("button", { name: "Roxtec" }));
    expect(await screen.findByRole("alertdialog")).toBeInTheDocument();
    await waitFor(() => expect(demoLoginCalls(fetchMock)).toBe(0));
    expect(getSession()).toMatchObject({ token: "pw.sig" });
  });
});
