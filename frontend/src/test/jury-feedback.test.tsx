import { fireEvent, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DeadlineBadge } from "@/components/shared/badges";
import { sortByDeadline } from "@/lib/utils";
import Collaboration from "@/pages/Collaboration";
import Opportunities from "@/pages/Opportunities";
import Overview from "@/pages/Overview";
import { HEALTH, mockFetch, renderPlain, renderWorkspace, signIn } from "./utils";

const item = (id: number, deadline_at: string | null, days_left: number | null) => ({ id, deadline_at, timeliness: { days_left } });

describe("funding deadline sorting", () => {
  it("orders upcoming (nearest first), then closed, then undated, without mutating the input", () => {
    const input = Object.freeze([
      item(1, null, null),
      item(2, "2027-01-19T13:00:00+00:00", 67),
      item(3, "2026-10-01T12:00:00+00:00", -43),
      item(4, "2026-11-17T12:00:00+00:00", 4),
      item(5, "not-a-date", null),
      item(6, "2027-01-19T13:00:00+00:00", 67),
      item(7, "2026-11-01T12:00:00+00:00", -12),
    ]);
    const before = JSON.stringify(input);
    const out = sortByDeadline(input);
    expect(out.map((x) => x.id)).toEqual([4, 2, 6, 7, 3, 1, 5]); // equal dates keep original order (2 before 6)
    expect(out).not.toBe(input);
    expect(JSON.stringify(input)).toBe(before);
  });
});

describe("deadline badge", () => {
  it("keeps the exact date for closed calls", () => {
    renderPlain(<DeadlineBadge deadline="2026-10-01T12:00:00+00:00" days={-43} />);
    expect(screen.getByText("1 Oct 2026 · Closed")).toBeInTheDocument();
  });

  it("makes same-day and soon-closing deadlines obvious", () => {
    renderPlain(<><DeadlineBadge deadline="2026-11-13T15:00:00+00:00" days={0} /><DeadlineBadge deadline="2026-11-17T12:00:00+00:00" days={4} /></>);
    expect(screen.getByText("13 Nov 2026 · Closes today")).toBeInTheDocument();
    expect(screen.getByText("17 Nov 2026 · 4 days left")).toBeInTheDocument();
  });

  it("handles unreadable dates without crashing or inventing one", () => {
    renderPlain(<DeadlineBadge deadline="not-a-date" days={null} />);
    expect(screen.getByText("Deadline unclear · check source")).toBeInTheDocument();
    expect(screen.queryByText(/Invalid Date/)).not.toBeInTheDocument();
  });
});

const CLAIM = (id: number, claim_type: "source_stated" | "inferred") => ({ id, label: `claim ${id}`, claim_type, status: "active" });
const COLLAB = {
  id: 1, partner_id: 7, score: 70.3, strength: "strong", status: "potential",
  partner: { id: 7, name: "Roxtec", slug: "roxtec", website: null, profile_level: "full", organisation_type: "company", membership_status: "verified", description: "Sealing systems." },
  location: { scopes: ["karlskrona", "blekinge", "sweden"], label: "Karlskrona, Blekinge", basis: "", verified: true, claim_ids: [] }, proximity: { value: 10, explanation: "" },
  criteria: [], core_capabilities: [], relevant_technologies: [],
  complementary_capabilities: { partner_offers: ["Cable & pipe sealing systems"], company_offers: [] },
  why: ["Ocean Harvesting documents offshore structures; Roxtec documents sealing systems."], scenario: "Joint sea-trial penetrations.",
  mutual_benefit: { for_company: "Certified sealing know-how.", for_partner: "A reference application." },
  rules: [{ rule: "r", relation: "component_supply", strength: 1, contribution: 1, direction: "", seeker_id: 6, provider_id: 7,
    need: { concept: "offshore", label: "Offshore & subsea structures", claims: [CLAIM(1, "source_stated")] },
    offer: { concept: "sealing", label: "Cable & pipe sealing systems", claims: [CLAIM(2, "inferred")] },
    rationale: "", scenario: "", seeker_benefit: "", provider_benefit: "", first_step: "", basis: "" }],
  shared_context: [], shared_opportunities: [], evidence_claim_ids: [1, 2], missing_information: [],
  uncertainties: ["Commercial interest is unknown."], first_step: "Request a technical scoping call.", disclaimer: "Potential collaboration only; nobody has agreed to collaborate.",
};

describe("Collaboration", () => {
  it("opens on the partner list, keeps the graph available and never claims a partnership", async () => {
    // jsdom has no ResizeObserver; React Flow needs one once the graph tab is opened.
    vi.stubGlobal("ResizeObserver", class { observe() {} unobserve() {} disconnect() {} });
    signIn();
    mockFetch((url) => {
      if (url.includes("/api/health")) return { body: HEALTH };
      if (url.includes("/collaborations")) return { body: { items: [COLLAB], method: "rules" } };
      if (url.includes("/graph")) return { body: { nodes: [], edges: [], legend: {}, disclaimer: "Potential collaboration only; nobody has agreed to collaborate." } };
      return undefined;
    });
    renderWorkspace("/app/6/collaboration", "/app/:companyId/collaboration", <Collaboration />);
    expect(await screen.findByRole("heading", { name: "Roxtec" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Recommended partners/ })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText("Potential — not a partnership")).toBeInTheDocument();
    expect(screen.getByText("Partly inferred")).toBeInTheDocument();
    expect(screen.getByText("What they offer")).toBeInTheDocument();
    expect(screen.getByText("Offshore & subsea structures")).toBeInTheDocument();
    expect(screen.getByText(/Request a technical scoping call/)).toBeInTheDocument();
    expect(screen.getByText("Commercial interest is unknown.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: /Explore ecosystem/ }));
    expect(screen.getByRole("tab", { name: /Explore ecosystem/ })).toHaveAttribute("aria-selected", "true");
  });
});

const OVERVIEW = {
  company: { id: 6, name: "Ocean Harvesting", tagline: null, website: null, membership_status: "verified", profile_level: "full" },
  summary: { headline: "h", bullets: [], generated_by: "template", as_of: "2026-11-13" },
  profile: { claims_by_type: { source_stated: 20, inferred: 2, user_provided: 0 }, completeness: 100, overview: null, pending_review: 2 },
  metrics: { relevant_opportunities: 5, opportunities_considered: 206, technologies_adopt_trial: 5, potential_partners: 5, high_priority_actions: 7 },
  top_opportunities: [], technologies: [],
  partners: [{ id: 7, name: "Roxtec", score: 70, strength: "strong", headline: "Sealing systems for offshore structures." }],
  top_recommendations: [{ id: 79, title: "Prepare an application", tier: "high", kind: "apply_funding", rank_score: 68, status: "open" }],
  deadlines: [{ id: 51, title: "The Baltic Challenge", deadline_at: "2026-12-02T13:00:00+00:00", days_left: 19, score: 43 }],
  freshness: { last_live_collection: null, last_collection_attempt: null, latest_record_retrieved_at: null, data_modes: [], label: "Snapshot", sources: [] },
};

describe("Overview next steps", () => {
  it("shows three concrete actions that link to existing workspace routes", async () => {
    signIn();
    mockFetch((url) => (url.includes("/api/health") ? { body: HEALTH } : url.includes("/overview") ? { body: OVERVIEW } : undefined));
    renderWorkspace("/app/6/overview", "/app/:companyId/overview", <Overview />);
    expect(await screen.findByText("Your next steps")).toBeInTheDocument();
    const steps = screen.getAllByRole("listitem").filter((li) => li.querySelector("h3"));
    expect(steps).toHaveLength(3);
    expect(within(steps[0]).getByRole("link", { name: /Review profile/ })).toHaveAttribute("href", "/app/6/company");
    expect(within(steps[1]).getByText("Next deadline: 2 Dec 2026 (19 days left)")).toBeInTheDocument();
    expect(within(steps[1]).getByRole("link", { name: /See all deadlines/ })).toHaveAttribute("href", "/app/6/opportunities?view=timeline");
    expect(within(steps[2]).getByText(/potential partner: Roxtec/)).toBeInTheDocument();
    expect(within(steps[2]).getByRole("link", { name: /View potential partners/ })).toHaveAttribute("href", "/app/6/collaboration");
  });
});

const EVENT = (id: number, title: string, published_at: string | null, recent: boolean) => ({
  id, external_id: String(id), title, title_original: null, description: null, purpose_text: null, eligibility_text: null, funding_text: null,
  category: "event", category_label: "Event", organisation: "Blue Science Park", programme: null, source_key: "bsp_events", source_name: "Blue Science Park — Events",
  source_url: `https://www.bluesciencepark.se/event/e${id}/`, apply_url: null, language: "sv", published_at, opens_at: null, deadline_at: null, deadline_status: "not_stated",
  rolling_assessment: false, decision_expected_at: null, provenance: "snapshot", retrieved_at: "2026-11-13T12:00:00+00:00", quality_flags: ["metadata_only", "event_date_not_in_metadata"],
  concepts: [], geo_scopes: ["karlskrona"], geo_basis: "Inferred", geo_inferred: true, event_format: "unknown", format_basis: null, evidence_id: null,
  timeliness: { status: "date_unknown", days_left: null, label: "Event date not in collected metadata", recent },
});

describe("Events view", () => {
  it("never invents dates or sponsors, sorts by listing date and links to the official page", async () => {
    signIn();
    const items = [EVENT(1, "Older event", "2023-05-02T10:00:00+00:00", false), EVENT(2, "Newer old event", "2026-02-03T11:14:53+00:00", false), EVENT(3, "Fresh listing", "2026-10-01T09:00:00+00:00", true)];
    const fetchMock = mockFetch((url) => {
      if (url.includes("/api/health")) return { body: HEALTH };
      if (url.includes("/opportunities")) return { body: { items, total: 3, page: 1, page_size: 100, relevant_threshold: 35, facets: { categories: [], sources: [], technologies: [], industries: [] } } };
      return undefined;
    });
    renderWorkspace("/app/6/opportunities?view=events", "/app/:companyId/opportunities", <Opportunities />);
    expect(await screen.findByText("Fresh listing")).toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([u]) => String(u).includes("category=event") && String(u).includes("min_score=0"))).toBe(true);
    const titles = screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent);
    expect(titles).toEqual(["Fresh listing", "Newer old event", "Older event"]);
    expect(screen.getByText("Older listings — may have passed")).toBeInTheDocument();
    expect(screen.getAllByText("Sponsor information not available in the collected event data.")).toHaveLength(3);
    expect(screen.getAllByText("Event date not in collected data")).toHaveLength(3);
    expect(screen.queryByText(/^(Upcoming|Happening today)$/)).not.toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /Official event page/ })[0]).toHaveAttribute("href", "https://www.bluesciencepark.se/event/e3/");
  });
});
