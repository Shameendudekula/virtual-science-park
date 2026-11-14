import { fireEvent, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SearchPage } from "@/pages/Tools";
import { HEALTH, mockFetch, renderWorkspace, signIn } from "./utils";

const QUERY = (text: string, intent = "opportunities") => ({ text, intent, company_id: null, company_name: null, concepts: [], categories: [], notes: [], parser: "deterministic rules (no LLM)" });
const SUGGESTIONS = ["Which funding opportunities are relevant to my company?", "Which companies have complementary expertise in marine technology?"];

const DECLINED = {
  query: QUERY("Write a romantic poem.", "none"), results: [], count: 0, note: "No search was run for this request.",
  boundary: { category: "out_of_scope", handling: "declined", message: "That request is outside what this service does. Virtual Science Park helps companies find funding.", suggestions: SUGGESTIONS, referral: null, classifier: "deterministic rules (no LLM)" },
};
const ELIGIBILITY = {
  query: QUERY("Confirm that this company is eligible for this funding programme."), count: 1, note: "Results are records from the VSP database.",
  results: [{ type: "opportunity", id: 43, title: "Industrial flexible energy control", score: 64, band: "strong", subtitle: "Vinnova", why: ["Shared technology areas"] }],
  boundary: { category: "eligibility", handling: "answered_with_notice", message: "These results are potential matches only. VSP does not assess formal eligibility and cannot guarantee funding.", suggestions: [], referral: { label: "Contact Blue Science Park staff via the official website", url: "https://www.bluesciencepark.se/" }, classifier: "deterministic rules (no LLM)" },
};

function setup(body: unknown) {
  signIn();
  return mockFetch((url) => {
    if (url.includes("/api/health")) return { body: HEALTH };
    if (url.includes("/api/search/history")) return { body: [] };
    if (url.includes("/api/search")) return { body };
    return undefined;
  });
}

describe("Ask VSP service boundaries", () => {
  it("shows the remit and suggestions instead of results for an unrelated request", async () => {
    const fetchMock = setup(DECLINED);
    renderWorkspace("/app/6/search?q=Write%20a%20romantic%20poem.", "/app/:companyId/search", <SearchPage />);
    expect(await screen.findByText("Outside what this service does")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(/outside what this service does/);
    expect(screen.queryByText("Interpreted as")).not.toBeInTheDocument();
    expect(screen.queryByText("No matching records")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: SUGGESTIONS[0] }));
    await waitFor(() => expect(fetchMock.mock.calls.some(([u]) => String(u).includes(encodeURIComponent(SUGGESTIONS[0])))).toBe(true));
  });

  it("shows potential matches with an eligibility notice and a staff referral", async () => {
    setup(ELIGIBILITY);
    renderWorkspace("/app/6/search?q=Confirm%20eligibility", "/app/:companyId/search", <SearchPage />);
    expect(await screen.findByText("Potential matches only — not an eligibility decision")).toBeInTheDocument();
    expect(screen.getByText(/does not assess formal eligibility/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Contact Blue Science Park staff/ })).toHaveAttribute("href", "https://www.bluesciencepark.se/");
    expect(screen.getByText("Industrial flexible energy control")).toBeInTheDocument();
  });
});
