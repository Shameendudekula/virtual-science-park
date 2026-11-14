import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ClaimTypeBadge, DeadlineBadge, LocationBadges, RegionalNote } from "@/components/shared/badges";
import { CriteriaBreakdown, Uncertainty } from "@/components/shared/explain";
import { EmptyState, ErrorState } from "@/components/ui/primitives";
import { ApiError } from "@/lib/api";
import { getSession, setSession } from "@/lib/session";
import { renderPlain } from "./utils";

describe("provenance and claim labelling", () => {
  it("distinguishes source-stated facts, inferences and company input", () => {
    renderPlain(<><ClaimTypeBadge type="source_stated" /><ClaimTypeBadge type="inferred" /><ClaimTypeBadge type="user_provided" /></>);
    expect(screen.getByText("Source-stated")).toHaveAttribute("title", "Stated in a cited public source");
    expect(screen.getByText("Inferred").getAttribute("title")).toMatch(/not a verified fact/);
    expect(screen.getByText("Company-provided")).toBeInTheDocument();
  });

  it("never shows an invented deadline", () => {
    renderPlain(<><DeadlineBadge deadline={null} /><DeadlineBadge deadline={null} status="placeholder_rejected" /></>);
    expect(screen.getByText("Deadline not stated in source")).toBeInTheDocument();
    expect(screen.getByText(/placeholder rejected/)).toBeInTheDocument();
  });

  it("labels inferred locations and online formats", () => {
    renderPlain(<LocationBadges scopes={["online", "karlskrona", "blekinge", "sweden"]} inferred />);
    expect(screen.getByText("Online")).toBeInTheDocument();
    expect(screen.getByText("Karlskrona · inferred")).toBeInTheDocument();
  });

  it("explains geographic relevance with its basis", () => {
    renderPlain(<RegionalNote geo={{ scopes: ["sweden"], labels: ["Sweden"], basis: "Inferred: Vinnova is Sweden's national innovation agency.", inferred: true, format: "not_applicable", format_basis: null, relevance_label: "National", explanation: "National programme — open across Sweden.", company_location: "Karlskrona, Blekinge" }} />);
    expect(screen.getByText(/open across Sweden/)).toBeInTheDocument();
    expect(screen.getByText(/Basis: Inferred/)).toBeInTheDocument();
  });
});

describe("explanations", () => {
  it("renders every criterion with value, maximum and explanation", () => {
    renderPlain(<CriteriaBreakdown criteria={[{ key: "technology_fit", label: "Technology fit", value: 20, max: 35, explanation: "Shared technology areas: Energy Systems" }]}
      penalties={[{ key: "domain_mismatch", value: -10, explanation: "Targets Food & Agriculture" }]} note="Not a probability" />);
    expect(screen.getByText("Technology fit")).toBeInTheDocument();
    expect(screen.getByText("20.0 / 35")).toBeInTheDocument();
    expect(screen.getByText(/Energy Systems/)).toBeInTheDocument();
    expect(screen.getByText(/Food & Agriculture/)).toBeInTheDocument();
    expect(screen.getByText("Not a probability")).toBeInTheDocument();
  });

  it("deduplicates uncertainty items and hides when empty", () => {
    const { container } = renderPlain(<Uncertainty items={[]} />);
    expect(container).toBeEmptyDOMElement();
    renderPlain(<Uncertainty items={["Eligibility not stated", "Eligibility not stated"]} />);
    expect(screen.getAllByText("Eligibility not stated")).toHaveLength(1);
  });
});

describe("empty and error states", () => {
  it("renders an empty state with guidance", () => {
    renderPlain(<EmptyState title="No opportunities" description="Lower the minimum relevance." />);
    expect(screen.getByText("No opportunities")).toBeInTheDocument();
    expect(screen.getByText(/Lower the minimum/)).toBeInTheDocument();
  });

  it("renders API errors with a retry action", () => {
    const retry = vi.fn();
    renderPlain(<ErrorState error={new ApiError(500, "internal_error", "An unexpected error occurred.")} onRetry={retry} />);
    expect(screen.getByRole("alert")).toHaveTextContent("An unexpected error occurred.");
    fireEvent.click(screen.getByRole("button", { name: /try again/i }));
    expect(retry).toHaveBeenCalled();
  });
});

describe("session storage", () => {
  it("survives unavailable storage and expires old sessions", () => {
    const spy = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("blocked"); });
    setSession({ token: "x", expires_at: Math.floor(Date.now() / 1000) + 60, company: { id: 1, name: "A", slug: "a" } });
    expect(getSession()?.company.id).toBe(1);
    spy.mockRestore();
    setSession({ token: "x", expires_at: Math.floor(Date.now() / 1000) - 10, company: { id: 1, name: "A", slug: "a" } });
    expect(getSession()).toBeNull();
    setSession(null);
  });
});
