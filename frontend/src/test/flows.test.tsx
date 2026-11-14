import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PriorityEditor } from "@/features/priorities";
import { setSession, getSession } from "@/lib/session";
import Focus from "@/pages/Focus";
import Opportunities from "@/pages/Opportunities";
import { HEALTH, mockFetch, renderPlain, renderWorkspace, signIn } from "./utils";

const GEO = { scopes: ["sweden"], labels: ["Sweden"], basis: "Inferred: Vinnova is Sweden's national innovation agency.", inferred: true, format: "not_applicable", format_basis: null, relevance_label: "National", explanation: "National programme.", company_location: "Karlskrona, Blekinge" };

const FOCUS = {
  company: { id: 6, name: "Ocean Harvesting", location: { scopes: ["karlskrona", "blekinge", "sweden"], label: "Karlskrona, Blekinge", basis: "stated", verified: true, claim_ids: [1] } },
  time_saved: { opportunities_screened: 206, sources: ["Vinnova"], relevant: 6, message: "VSP screened 206 records from 3 sources; 6 are worth your time." },
  top_three: [
    { id: 1, title: "Develop a research proposal: Industrial flexible energy control", tier: "high", kind: "research_proposal", status: "open", why: ["Shared technology areas: Energy Systems & Storage"], next_step: "Read the source's 'who can apply' text.", source: { label: "Open source (Vinnova)", url: "https://data.vinnova.se/api/ansokningsomgangar/2026-02019" }, geography: GEO },
    { id: 2, title: "Explore a potential collaboration with Roxtec", tier: "high", kind: "contact_partner", status: "open", why: ["Offshore sealing complementarity"], next_step: "Request a technical scoping call.", source: null, geography: null },
  ],
  deadlines: [], new_opportunities: [], local_events: [],
  regional_partners: [{ id: 7, name: "Roxtec", score: 70, strength: "strong", location: { scopes: ["karlskrona", "blekinge", "sweden"], label: "Karlskrona, Blekinge", basis: "", verified: true, claim_ids: [] }, proximity: "Both have a verified presence in Blekinge.", why: ["Complementary sealing"], first_step: "Request a call.", website: null }],
  wider_partners: [], technologies: [], saved: [], saved_count: 0,
  priorities: [{ key: "find_funding", label: "Find new funding", description: "Grants", weight: 1 }],
  freshness: "Previously collected snapshot (not live)",
};

afterEach(() => {
  vi.unstubAllGlobals();
  act(() => setSession(null));
});

describe("Your Innovation Opportunities", () => {
  it("shows three explained actions with next steps and nearby partners", async () => {
    signIn();
    mockFetch((url) => (url.includes("/api/health") ? { body: HEALTH } : url.includes("/focus") ? { body: FOCUS } : undefined));
    renderWorkspace("/app/6/focus", "/app/:companyId/focus", <Focus />);
    expect(await screen.findByText("What Ocean Harvesting should look at this week")).toBeInTheDocument();
    expect(screen.getByText(/Industrial flexible energy control/)).toBeInTheDocument();
    expect(screen.getAllByText(/Next step:/).length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("Both have a verified presence in Blekinge.")).toBeInTheDocument();
    expect(screen.getByText(/screened 206 records/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open source \(Vinnova\)/ })).toHaveAttribute("href", expect.stringContaining("data.vinnova.se"));
  });

  it("handles an API failure without crashing", async () => {
    signIn();
    mockFetch((url) => (url.includes("/api/health") ? { body: HEALTH } : { status: 500, body: { error: { code: "internal_error", message: "An unexpected error occurred." } } }));
    renderWorkspace("/app/6/focus", "/app/:companyId/focus", <Focus />);
    expect(await screen.findByRole("alert")).toHaveTextContent("An unexpected error occurred.");
    expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
  });

  it("shows a clear message when the API is unreachable", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("Failed to fetch"); }));
    renderWorkspace("/app/6/focus", "/app/:companyId/focus", <Focus />);
    expect(await screen.findByText("The API is not reachable")).toBeInTheDocument();
  });

  it("opens a demo workspace automatically in demo mode", async () => {
    const fetchMock = mockFetch((url) => {
      if (url.includes("/api/health")) return { body: HEALTH };
      if (url.includes("/api/auth/demo-login")) return { body: { token: "a.b", expires_at: Math.floor(Date.now() / 1000) + 3600, company: { id: 6, name: "Ocean Harvesting", slug: "ocean-harvesting" } } };
      if (url.includes("/focus")) return { body: FOCUS };
      return undefined;
    });
    renderWorkspace("/app/6/focus", "/app/:companyId/focus", <Focus />);
    expect(await screen.findByText("What Ocean Harvesting should look at this week")).toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([u]) => String(u).includes("/api/auth/demo-login"))).toBe(true);
    const focusCall = fetchMock.mock.calls.find(([u]) => String(u).includes("/focus"))!;
    expect(new Headers(focusCall[1]?.headers).get("Authorization")).toBe("Bearer a.b");
    expect(getSession()?.company.id).toBe(6);
  });
});

describe("priority changes", () => {
  it("sends new weights and shows how the ranking moved", async () => {
    signIn();
    const fetchMock = mockFetch((url, init) =>
      url.includes("/priorities") && init?.method === "PUT"
        ? { body: { result: {}, ranking_changes: [{ fingerprint: "partner:4", id: 9, title: "Explore a potential collaboration with Kiwa", change: "up", before: { position: 13, tier: "later", score: 38 }, after: { position: 4, tier: "high", score: 59 } }] } }
        : undefined);
    renderPlain(<PriorityEditor companyId={6} priorities={[{ key: "testing_facilities", label: "Find testing facilities", description: "", weight: 1 }]} />);
    const update = screen.getByRole("button", { name: /update recommendations/i });
    expect(update).toBeDisabled();
    fireEvent.click(screen.getByRole("radio", { name: "Top" }));
    fireEvent.click(update);
    expect(await screen.findByText("Explore a potential collaboration with Kiwa")).toBeInTheDocument();
    expect(screen.getByText("#13 → #4")).toBeInTheDocument();
    const body = JSON.parse(String(fetchMock.mock.calls[0][1]?.body));
    expect(body.weights.testing_facilities).toBe(3);
  });
});

describe("Opportunity Radar", () => {
  const OPP = {
    id: 43, external_id: "2026-02019", title: "Industrial flexible energy control with advanced digitalization", title_original: null, description: "x", purpose_text: "x",
    eligibility_text: null, funding_text: null, category: "research_funding", category_label: "Research funding", organisation: "Vinnova", programme: "Advanced digitalization",
    source_key: "vinnova", source_name: "Vinnova", source_url: "https://data.vinnova.se/api/ansokningsomgangar/2026-02019", apply_url: null, language: "en",
    published_at: null, opens_at: null, deadline_at: "2027-01-19T13:00:00+00:00", deadline_status: "stated", rolling_assessment: false, decision_expected_at: null,
    provenance: "snapshot", retrieved_at: "2026-11-13T12:00:00+00:00", quality_flags: [], concepts: [], geo_scopes: ["sweden"], geo_basis: "Inferred", geo_inferred: true,
    event_format: "not_applicable", format_basis: null, evidence_id: 1, timeliness: { status: "open", days_left: 67, label: "Open — 67 days left" },
    match: { relevance_score: 66, relevance_band: "strong", reasons: ["Shared technology areas: Energy Systems & Storage"], criteria: [], penalties: [] },
  };

  it("renders ranked cards with reasons and applies the region filter", async () => {
    signIn();
    const fetchMock = mockFetch((url) => {
      if (url.includes("/api/health")) return { body: HEALTH };
      if (url.includes("/opportunities")) return { body: { items: [OPP], total: 1, page: 1, page_size: 100, relevant_threshold: 35, facets: { categories: [], sources: ["vinnova"], technologies: [], industries: [] } } };
      return undefined;
    });
    renderWorkspace("/app/6/opportunities", "/app/:companyId/opportunities", <Opportunities />);
    expect(await screen.findByText(OPP.title)).toBeInTheDocument();
    expect(screen.getByText(/Energy Systems & Storage/)).toBeInTheDocument();
    expect(screen.getByText("66 · strong")).toBeInTheDocument();
    expect(screen.getByText("Collected snapshot")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Region"), { target: { value: "blekinge" } });
    await waitFor(() => expect(fetchMock.mock.calls.some(([u]) => String(u).includes("region=blekinge"))).toBe(true));
  });

  it("shows an empty state when nothing matches", async () => {
    signIn();
    mockFetch((url) => (url.includes("/api/health") ? { body: HEALTH } : url.includes("/opportunities") ? { body: { items: [], total: 0, page: 1, page_size: 100, relevant_threshold: 35, facets: { categories: [], sources: [], technologies: [], industries: [] } } } : undefined));
    renderWorkspace("/app/6/opportunities", "/app/:companyId/opportunities", <Opportunities />);
    expect(await screen.findByText("No opportunities match these filters")).toBeInTheDocument();
  });
});
