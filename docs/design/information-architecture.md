# Information Architecture

**Status:** Proposal. Routes and navigation are design proposals; API endpoints are taken unchanged from [../api-contract.md](../api-contract.md). No new endpoints are introduced. Where the UI needs something the API does not offer, it is marked **Gap** and listed in [design-decisions.md](design-decisions.md#still-pending) and [api-ui-consistency.md](api-ui-consistency.md).

## A. Sitemap

```mermaid
flowchart TD
    classDef p0 fill:#E6F4F2,stroke:#0E6B66,color:#0F1B2D
    classDef p1 fill:#FFFFFF,stroke:#76869E,color:#0F1B2D,stroke-dasharray: 4 3
    classDef p2 fill:#F7F5F0,stroke:#A9B6C8,color:#4A5A72,stroke-dasharray: 2 4

    L["01 Welcome / Landing<br/>(P1)"]:::p1
    CS["02 Company selection<br/>(P0)"]:::p0
    subgraph WS["Company workspace — scoped to one company (simulated sign-in)"]
        D["03 Dashboard<br/>(P0)"]:::p0
        P["04 Intelligence profile<br/>(P0)"]:::p0
        R["05 Review & refine mode<br/>(P0)"]:::p0
        F["06 Findings discovery<br/>(P0)"]:::p0
        FD["07 Finding detail<br/>(P0)"]:::p0
        A["08 Innovation assistant<br/>(P0)"]:::p0
        C["09 Connections<br/>(P2)"]:::p2
        S["10 Settings & preferences<br/>(P2, feedback parts P1)"]:::p2
    end
    T["12 Sources & transparency<br/>(P1)"]:::p1
    ST["11 Staff view — separate scope<br/>(P2)"]:::p2

    L --> CS --> D
    D --> P --> R
    D --> F --> FD
    D --> A
    FD --> A
    R -. "impact summary" .-> F
    D --> C
    D --> S
    CS --> T
    D --> T
```

Legend: solid teal = **P0** (MVP); dashed = **P1**; dotted grey = **P2** (future, design only).

## Routes (proposal)

| # | Screen | Route | Data (existing endpoints) | Priority |
|---|---|---|---|---|
| 01 | Welcome / landing | `/` (P1). In P0, `/` redirects to `/companies` | Static | P1 |
| 02 | Company selection | `/companies` | `GET /companies` | P0 |
| 03 | Dashboard | `/c/:companyId` | `GET /companies/{id}`, `GET /companies/{id}/profile`, `GET /companies/{id}/matches?limit=…` | P0 |
| 04 | Intelligence profile | `/c/:companyId/profile` | `GET /companies/{id}/profile` | P0 |
| 05 | Refine (part of 04; no separate mode, DD-09) | `/c/:companyId/profile` | `PATCH …/profile/claims/{claim_id}`, `POST …/profile/claims`, then `GET …/matches` | P0 |
| 06 | Findings discovery | `/c/:companyId/findings?type=funding\|event\|update` | `GET /companies/{id}/matches?type=` | P0 |
| 07 | Finding detail | `/c/:companyId/findings/:matchId` | The match from the cached `GET …/matches` response (**Gap:** no `GET /matches/{id}`; see [DD-12](design-decisions.md)) | P0 |
| 08 | Innovation assistant | `/c/:companyId/assistant` | `POST /companies/{id}/ask` | P0 |
| 09 | Connections | `/c/:companyId/connections` | None (FR-M12 is P2; no endpoint) | P2 |
| 10 | Settings & preferences | `/c/:companyId/settings` | Feedback and saved items: P1 endpoints; others none | P2 (P1 parts) |
| 11 | Staff view | `/staff` (separate scope) | None (FR-U12 is P2; no endpoint) | P2 |
| 12 | Sources & transparency | `/about` | Static content from [../sources.md](../sources.md); `GET /sources` is P1 | P1 |

## Navigation Model

- **Global (outside a workspace):** a slim top bar with the product wordmark and an "About this prototype" link (P1). Company selection is the entry point.
- **Workspace shell (inside `/c/:companyId`):**
  - **Left sidebar (240 px, navy; replaced by a top tab bar ≤ 900 px):**
    - Dashboard
    - Profile
    - Findings, with sub-items Funding · Events · Updates
    - Assistant
    - Below a divider, *Future*: Connections and Settings. In P0 these are hidden; in the clickable prototype they are shown disabled with a "Planned" chip.
  - **Top bar:**
    - company switcher, labelled "Acting as: {Company} · Simulated sign-in" (FR-U01, FR-S06);
    - "Ask the assistant" shortcut;
    - profile review status chip.
  - **Prototype banner** (always visible, FR-U07): "Prototype · Opportunity data is a dated snapshot · Sign-in is simulated · [What's real?]"
- **Breadcrumbs** on the detail and review screens only.
- **Switching company** resets workspace state and clears the assistant panel, so no cross-company context is left on screen (BR-19).

## Content Hierarchy per Workspace

```text
Company
├── Profile (version, last researched date, missing_fields)
│   └── Claims grouped by the brief's categories (p.2)
│       └── Evidence (quote, source link, retrieved date)
├── Findings (matches)
│   ├── Funding   — purpose, deadline, eligibility summary, potential-match label
│   ├── Events    — format, audience, dates, location
│   └── Updates   — published date, what changed
│       └── each: why it matches (cited claims), next step, uncertainties, source, data status, disclaimer
└── Assistant (private to this company)
```

## F. Data Flow (frontend ↔ backend ↔ agents ↔ sources ↔ database)

```mermaid
flowchart LR
    classDef mvp fill:#E6F4F2,stroke:#0E6B66,color:#0F1B2D
    classDef ext fill:#FBF0D9,stroke:#7A4B00,color:#0F1B2D
    classDef future fill:#F7F5F0,stroke:#A9B6C8,color:#4A5A72,stroke-dasharray: 3 3

    subgraph Browser
        UI["React + TypeScript UI"]:::mvp
    end
    subgraph Backend["FastAPI backend (single process)"]
        API["REST API /api/v1<br/>company-scope check"]:::mvp
        PA["Profiling agent"]:::mvp
        MA["Monitoring agents"]:::mvp
        MT["Matching agent"]:::mvp
        AS["Assistant<br/>scope guard + responder"]:::mvp
        GW["LLM gateway<br/>(no tools, schema-validated)"]:::mvp
        CLI["Demo build CLI"]:::mvp
        SCHED["Scheduler / job queue"]:::future
    end
    DB[("SQLite<br/>profiles · claims · evidence ·<br/>opportunities · matches · interactions")]:::mvp
    WEB["Member websites<br/>(allowlist)"]:::ext
    SRC["Public sources<br/>S1 funding · S3 events/updates"]:::ext
    LLM["LLM provider<br/>(TBD, Q-05)"]:::ext

    UI -- "JSON + X-Company-Token" --> API
    API --> DB
    API --> MT
    API --> AS
    CLI --> PA
    CLI --> MA
    PA -- "fetch (untrusted)" --> WEB
    MA -- "fetch (untrusted)" --> SRC
    PA --> GW
    MT --> GW
    AS --> GW
    GW --> LLM
    PA --> DB
    MA --> DB
    MT --> DB
    AS --> DB
    SCHED -.-> PA
    SCHED -.-> MA
```

- **MVP:** solid boxes. Profiling and collection run from the CLI; matching and the assistant are served through the API.
- **Future:** dashed boxes (scheduler, P2).
- **Untrusted inputs:** amber boxes.

The browser never calls sources or the LLM directly ([../architecture.md](../architecture.md#frontend-and-backend-responsibilities)).
