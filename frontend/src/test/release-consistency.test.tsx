import { act, fireEvent, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api, post } from "@/lib/api";
import { getSession, setAdminToken, setSession } from "@/lib/session";
import { SettingsPage } from "@/pages/Admin";
import Overview from "@/pages/Overview";
import { HEALTH, mockFetch, renderPlain, renderWorkspace } from "./utils";

const EXP = () => Math.floor(Date.now() / 1000) + 3600;
const OCEAN = { id: 6, name: "Ocean Harvesting", slug: "ocean-harvesting" };
const companySession = (readOnly: boolean) => setSession({ token: "company.sig", expires_at: EXP(), company: OCEAN, read_only: readOnly });
const ADMIN_TOKEN = "test-only-admin-token";
const UNAUTHORIZED = { status: 401, body: { error: { code: "unauthorized", message: "A valid admin token is required (X-Admin-Token header)." } } };

afterEach(() => {
  vi.unstubAllGlobals();
  act(() => { setSession(null); setAdminToken(null); });
});

// ------------------------------------------------------------------------------------------- Task 2: session handling
describe("401 handling", () => {
  it("a refused admin-only action keeps the company session", async () => {
    companySession(false);
    mockFetch((url) => (url.includes("/api/demo/reset") ? UNAUTHORIZED : undefined));
    await expect(post("/api/demo/reset", undefined, { adminOnly: true })).rejects.toMatchObject({ status: 401 });
    expect(getSession()).toMatchObject({ token: "company.sig" });
  });

  it("a genuine company-session failure still ends the session", async () => {
    companySession(false);
    mockFetch(() => ({ status: 401, body: { error: { code: "unauthorized", message: "Session expired or invalid. Please sign in again." } } }));
    await expect(api("/api/companies/6/overview")).rejects.toMatchObject({ status: 401 });
    expect(getSession()).toBeNull();
  });

  it("sends the admin token only for admin requests and keeps it out of company calls", async () => {
    companySession(false);
    setAdminToken(ADMIN_TOKEN);
    const fetchMock = mockFetch(() => ({ body: {} }));
    await api("/api/companies/6/overview");
    await post("/api/demo/reset", undefined, { adminOnly: true });
    const headers = fetchMock.mock.calls.map(([, init]) => new Headers(init?.headers).get("X-Admin-Token"));
    expect(headers).toEqual([null, ADMIN_TOKEN]);
  });
});

// ------------------------------------------------------------------------------------------- Task 1: Settings reset
function settingsBackend({ isAdmin, reset = { body: { status: "reset" } }, serverHasAdmin = true }: { isAdmin: boolean; reset?: { status?: number; body: unknown }; serverHasAdmin?: boolean }) {
  return mockFetch((url) => {
    if (url.includes("/api/health")) return { body: { ...HEALTH, admin_actions_enabled: serverHasAdmin } };
    if (url.includes("/api/auth/me")) return { body: { authenticated: true, is_admin: isAdmin, read_only: false, company: OCEAN, demo_mode: true } };
    if (url.includes("/api/demo/reset")) return reset;
    return undefined;
  });
}
const resetButton = () => screen.queryByRole("button", { name: /reset demo workspace/i });
const meCalls = (f: ReturnType<typeof mockFetch>) => f.mock.calls.filter(([u]) => String(u).includes("/api/auth/me")).length;

describe("Settings: demo reset is offered only to a verified admin", () => {
  it("without an admin token there is no reset control and no admin check", async () => {
    companySession(true);
    const fetchMock = settingsBackend({ isAdmin: false });
    renderPlain(<SettingsPage />);
    expect(await screen.findByText(/The reset requires the admin token/)).toBeInTheDocument();
    expect(resetButton()).not.toBeInTheDocument();
    expect(meCalls(fetchMock)).toBe(0);
  });

  it("an admin token the server does not accept shows no reset control", async () => {
    companySession(false);
    setAdminToken(ADMIN_TOKEN);
    settingsBackend({ isAdmin: false });
    renderPlain(<SettingsPage />);
    expect(await screen.findByText(/The saved admin token was not accepted/)).toBeInTheDocument();
    expect(resetButton()).not.toBeInTheDocument();
    expect(getSession()).toMatchObject({ token: "company.sig" });
  });

  it("a verified admin can reset; the request carries the admin token", async () => {
    companySession(false);
    setAdminToken(ADMIN_TOKEN);
    const fetchMock = settingsBackend({ isAdmin: true });
    renderPlain(<SettingsPage />);
    fireEvent.click(await screen.findByRole("button", { name: /reset demo workspace/i }));
    expect(await screen.findByText("Workspace reset to a clean state.")).toBeInTheDocument();
    const call = fetchMock.mock.calls.find(([u]) => String(u).includes("/api/demo/reset"))!;
    expect(new Headers(call[1]?.headers).get("X-Admin-Token")).toBe(ADMIN_TOKEN);
    expect(getSession()).toMatchObject({ token: "company.sig" });
  });

  it("a refused reset shows a safe error and keeps the company session", async () => {
    companySession(false);
    setAdminToken(ADMIN_TOKEN);
    settingsBackend({ isAdmin: true, reset: UNAUTHORIZED });
    renderPlain(<SettingsPage />);
    fireEvent.click(await screen.findByRole("button", { name: /reset demo workspace/i }));
    expect(await screen.findByText(/Reset failed\. A valid admin token is required/)).toBeInTheDocument();
    expect(screen.queryByText("Workspace reset to a clean state.")).not.toBeInTheDocument();
    expect(getSession()).toMatchObject({ token: "company.sig" });
  });

  it("says the reset is unavailable when the server has no admin token configured", async () => {
    companySession(false);
    setAdminToken(ADMIN_TOKEN);
    settingsBackend({ isAdmin: false, serverHasAdmin: false });
    renderPlain(<SettingsPage />);
    expect(await screen.findByText(/Not available: the server has no admin token configured/)).toBeInTheDocument();
    expect(resetButton()).not.toBeInTheDocument();
  });

  it("does not describe demo mode as allowing edits or resets", async () => {
    companySession(true);
    settingsBackend({ isAdmin: false });
    renderPlain(<SettingsPage />);
    expect(await screen.findByText("On (password-free, read-only demo login)")).toBeInTheDocument();
    expect(screen.queryByText(/Demo mode is off: reset requires/)).not.toBeInTheDocument();
  });
});

// ------------------------------------------------------------------------------------------- Task 3: Overview
const OVERVIEW = {
  company: { id: 6, name: "Ocean Harvesting", tagline: null, website: null, membership_status: "verified", profile_level: "full" },
  summary: { headline: "h", bullets: [], generated_by: "template", as_of: "2026-11-13" },
  profile: { claims_by_type: { source_stated: 20, inferred: 2, user_provided: 0 }, completeness: 100, overview: null, pending_review: 2 },
  metrics: { relevant_opportunities: 5, opportunities_considered: 206, technologies_adopt_trial: 5, potential_partners: 5, high_priority_actions: 7 },
  top_opportunities: [], technologies: [], partners: [],
  top_recommendations: [{ id: 79, title: "Prepare an application", tier: "high", kind: "apply_funding", rank_score: 68, status: "open" }],
  deadlines: [{ id: 51, title: "The Baltic Challenge", deadline_at: "2026-12-02T13:00:00+00:00", days_left: 19, score: 43 }],
  freshness: { last_live_collection: null, last_collection_attempt: null, latest_record_retrieved_at: null, data_modes: [], label: "Snapshot", sources: [] },
};

async function nextStepItems() {
  await screen.findByText("Your next steps");
  return screen.getAllByRole("listitem").filter((li) => li.querySelector("h3"));
}

describe("Overview next steps respect the session's permissions", () => {
  it("read-only visitors are pointed at viewing, never at confirming or editing", async () => {
    companySession(true);
    mockFetch((url) => (url.includes("/api/health") ? { body: HEALTH } : url.includes("/overview") ? { body: OVERVIEW } : undefined));
    renderWorkspace("/app/6/overview", "/app/:companyId/overview", <Overview />);
    const steps = await nextStepItems();
    expect(within(steps[0]).getByText("See how the profile was built")).toBeInTheDocument();
    expect(within(steps[0]).getByRole("link", { name: /View profile/ })).toHaveAttribute("href", "/app/6/company");
    expect(screen.queryByText(/Confirm or correct/)).not.toBeInTheDocument();
    expect(screen.queryByText(/^Review 2 inferred profile items$/)).not.toBeInTheDocument();
  });

  it("password sessions keep the editing suggestion", async () => {
    companySession(false);
    mockFetch((url) => (url.includes("/api/health") ? { body: HEALTH } : url.includes("/overview") ? { body: OVERVIEW } : undefined));
    renderWorkspace("/app/6/overview", "/app/:companyId/overview", <Overview />);
    const steps = await nextStepItems();
    expect(within(steps[0]).getByText("Review 2 inferred profile items")).toBeInTheDocument();
    expect(within(steps[0]).getByText(/Confirm or correct them/)).toBeInTheDocument();
    expect(within(steps[0]).getByRole("link", { name: /Review profile/ })).toHaveAttribute("href", "/app/6/company");
  });
});
