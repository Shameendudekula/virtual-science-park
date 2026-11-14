import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { AppShell } from "@/components/layout/AppShell";
import { PriorityEditor } from "@/features/priorities";
import { setSession } from "@/lib/session";
import { SearchPage } from "@/pages/Tools";
import { HEALTH, mockFetch, renderPlain, renderWorkspace } from "./utils";

const PRIORITIES = [{ key: "testing_facilities", label: "Find testing facilities", description: "", weight: 1 }];

function session(readOnly: boolean) {
  setSession({ token: "t.sig", expires_at: Math.floor(Date.now() / 1000) + 3600, company: { id: 6, name: "Ocean Harvesting", slug: "ocean-harvesting" }, read_only: readOnly });
}

afterEach(() => setSession(null));

describe("read-only public demo", () => {
  it("disables saving priorities and explains why, without sending a write", () => {
    session(true);
    const fetchMock = mockFetch(() => undefined);
    renderPlain(<PriorityEditor companyId={6} priorities={PRIORITIES} />);
    fireEvent.click(screen.getByRole("radio", { name: "Top" }));
    const update = screen.getByRole("button", { name: /update recommendations/i });
    expect(update).toBeDisabled();
    expect(screen.getAllByText(/Read-only demo: sign in/).length).toBeGreaterThan(0);
    fireEvent.click(update);
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === "PUT")).toBe(false);
  });

  it("keeps editing available for a password session", () => {
    session(false);
    mockFetch(() => undefined);
    renderPlain(<PriorityEditor companyId={6} priorities={PRIORITIES} />);
    fireEvent.click(screen.getByRole("radio", { name: "Top" }));
    expect(screen.getByRole("button", { name: /update recommendations/i })).toBeEnabled();
    expect(screen.queryByText(/Read-only demo/)).not.toBeInTheDocument();
  });

  it("shows a read-only banner with a sign-in link in the workspace", async () => {
    session(true);
    mockFetch((url) => (url.includes("/api/health") ? { body: HEALTH } : undefined));
    renderWorkspace("/app/6/overview", "/app/:companyId/*", <AppShell />);
    expect(await screen.findByText("Read-only demo.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign in to edit" })).toHaveAttribute("href", "/login?company=6");
  });

  it("does not request private question history in a read-only session", async () => {
    session(true);
    const fetchMock = mockFetch((url) => {
      if (url.includes("/api/health")) return { body: HEALTH };
      if (url.includes("/api/search?")) return { body: { query: { text: "wave energy funding", intent: "opportunities", company_id: 6, company_name: "Ocean Harvesting", concepts: [], categories: [], notes: [], parser: "deterministic rules (no LLM)" }, results: [], count: 0, note: "", boundary: { category: "in_scope", handling: "answered", message: null, suggestions: [], referral: null, classifier: "x" } } };
      return undefined;
    });
    renderWorkspace("/app/6/search?q=wave%20energy%20funding", "/app/:companyId/search", <SearchPage />);
    expect(await screen.findByText("Question history is not kept in the read-only demo.")).toBeInTheDocument();
    await waitFor(() => expect(fetchMock.mock.calls.some(([u]) => String(u).includes("/api/search?"))).toBe(true));
    expect(fetchMock.mock.calls.some(([u]) => String(u).includes("/api/search/history"))).toBe(false);
  });
});
