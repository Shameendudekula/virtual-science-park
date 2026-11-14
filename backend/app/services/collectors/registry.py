"""Configurable source registry. Adding a source = add a definition here + (optionally) a collector adapter."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SourceDefinition:
    key: str
    name: str
    publisher: str
    source_type: str
    base_url: str | None
    description: str
    license_note: str
    allowed_hosts: tuple[str, ...] = ()
    collectable: bool = True
    enabled: bool = True
    llm_allowed: bool = False
    disabled_reason: str | None = None
    extra: dict = field(default_factory=dict)


SOURCES: tuple[SourceDefinition, ...] = (
    SourceDefinition(
        key="vinnova",
        name="Vinnova open data — calls and application rounds",
        publisher="Vinnova (Sweden's Innovation Agency)",
        source_type="public_api",
        base_url="https://data.vinnova.se/api/",
        description="Funding calls (utlysningar) and application rounds (ansökningsomgångar) from Vinnova's public open-data API. "
        "Rounds become opportunities; calls provide programme names. Contact persons are deliberately not collected.",
        license_note="Public open-data API published by Vinnova. Titles, dates and call texts are shown with attribution and a link to the "
        "official record. Contact-person data in the API is excluded (data minimisation).",
        allowed_hosts=("data.vinnova.se",),
        llm_allowed=True,
    ),
    SourceDefinition(
        key="bsp_members",
        name="Blue Science Park — member directory",
        publisher="Blue Science Park",
        source_type="directory",
        base_url="https://www.bluesciencepark.se/wp-json/wp/v2/medlem",
        description="Public member listing used only to verify Blue Science Park membership (name, link, last modified).",
        license_note="Only minimum metadata (member name, URL, modified date) is collected. Page content is not copied. "
        "robots.txt allows crawling; reuse rights for page content have not been confirmed, so content is not reused or sent to any LLM.",
        allowed_hosts=("www.bluesciencepark.se", "bluesciencepark.se"),
    ),
    SourceDefinition(
        key="bsp_news",
        name="Blue Science Park — news posts",
        publisher="Blue Science Park",
        source_type="public_api",
        base_url="https://www.bluesciencepark.se/wp-json/wp/v2/posts",
        description="Ecosystem news metadata (title, date, link) used for discovery of programmes, test environments and ecosystem signals.",
        license_note="Metadata only (title, date, link). Article bodies are not stored or reused and are never sent to an external LLM.",
        allowed_hosts=("www.bluesciencepark.se", "bluesciencepark.se"),
    ),
    SourceDefinition(
        key="bsp_events",
        name="Blue Science Park — events",
        publisher="Blue Science Park",
        source_type="public_api",
        base_url="https://www.bluesciencepark.se/wp-json/wp/v2/event",
        description="Event metadata (title, publication date, link). Event dates are not part of the collected metadata.",
        license_note="Metadata only (title, date, link). Event descriptions are not stored or reused and are never sent to an external LLM.",
        allowed_hosts=("www.bluesciencepark.se", "bluesciencepark.se"),
    ),
    SourceDefinition(
        key="company_websites",
        name="Official company websites — evidence verification",
        publisher="Respective companies",
        source_type="website",
        base_url=None,
        description="Short excerpts from official company websites that support each source-stated profile claim. "
        "The collector re-fetches each page and checks that every excerpt is still present.",
        license_note="Short attributed excerpts are quoted only to evidence specific claims, with a link to the original page.",
        allowed_hosts=(
            "oceanharvesting.com", "cleura.com", "www.roxtec.com", "www.bth.se", "www.kiwa.com", "www.dnv.com", "www.nkt.com",
        ),
    ),
    SourceDefinition(
        key="eu_funding_tenders",
        name="EU Funding & Tenders Portal",
        publisher="European Commission",
        source_type="public_api",
        base_url="https://ec.europa.eu/info/funding-tenders/opportunities/portal/",
        description="Adapter slot for EU-level calls (Horizon Europe, Digital Europe, CETP).",
        license_note="Not activated. The search API terms and stable query parameters have not been reviewed for this prototype.",
        allowed_hosts=("api.tech.ec.europa.eu",),
        enabled=False,
        disabled_reason="Not activated: requires review of the EU Funding & Tenders search API terms before use. The application does not depend on it.",
    ),
    SourceDefinition(
        key="ymner",
        name="Ymner — funding discovery (external link)",
        publisher="Ymner",
        source_type="external_link",
        base_url="https://www.ymner.com/",
        description="Funding search service recommended by Blue Science Park. Shown as an external discovery link; not integrated.",
        license_note="Investigated 2026-11-13: robots.txt allows crawling, but the data API requires authentication (HTTP 401), no public "
        "API, feed or export is documented, and the terms of use are only rendered client-side, so reuse rights could not be confirmed. "
        "No data is collected. The adapter slot is ready if a permitted integration (API key or export) is agreed with Ymner.",
        allowed_hosts=("www.ymner.com",),
        enabled=False,
        disabled_reason="No permitted integration available: Ymner's API requires authentication and no public feed/export or reuse terms "
        "were found. Use the external link instead.",
        extra={"external_link": "https://www.ymner.com/"},
    ),
    SourceDefinition(
        key="user_input",
        name="Company representative input",
        publisher="Workspace users",
        source_type="user",
        base_url=None,
        description="Priorities, corrections and additions entered by company representatives in the profile editor.",
        license_note="Stored per company; kept separate from public source facts.",
        collectable=False,
    ),
    SourceDefinition(
        key="vsp_knowledge_base",
        name="VSP knowledge base (rules and taxonomy)",
        publisher="Virtual Science Park",
        source_type="curated",
        base_url=None,
        description="Authored technology taxonomy, adjacency hypotheses and complementarity rules used by the matching engine.",
        license_note="Authored content. Everything derived from it is labelled as rule-based inference.",
        collectable=False,
    ),
)

SOURCE_BY_KEY = {s.key: s for s in SOURCES}
