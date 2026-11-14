"""The VSP knowledge base: concepts, technology radar items, industries and capabilities.

This is authored domain knowledge (not source data). Everything derived from it is labelled as
rule-based inference in the UI. Terms are matched case-insensitively with word boundaries; a term
ending in '*' matches any suffix (useful for Swedish compounds); a term starting with 'CS:' is
matched case-sensitively (e.g. acronyms such as 'AI' or 'PTO').

Specificity expresses how much a match on this concept should count:
  1.0  specific  (e.g. 'wave energy converter', 'OpenStack', 'cable transit')
  0.6  broad     (e.g. 'energy', 'industry', 'cloud')
  0.3  weak      (e.g. 'digital')
Generic words ('innovation', 'sustainable', 'system', 'future') are deliberately NOT concepts,
so sharing them never creates relevance.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Concept:
    key: str
    label: str
    kind: str  # technology | domain | capability
    terms: tuple[str, ...]
    specificity: float = 1.0
    implies: tuple[str, ...] = ()
    area: str | None = None  # radar quadrant (technology only)
    description: str = ""


RADAR_AREAS = ("Digital & AI", "Connectivity & Infrastructure", "Energy & Climate", "Industrial & Materials")

# --------------------------------------------------------------------------------------------
# Technology radar items
# --------------------------------------------------------------------------------------------
TECHNOLOGIES: tuple[Concept, ...] = (
    Concept("artificial_intelligence", "Artificial Intelligence", "technology",
            ("artificial intelligence", "CS:AI", "generative ai", "artificiell intelligens", "CS:AI-*", "sovereign ai", "agentbaserade", "agentic"),
            0.9, area="Digital & AI",
            description="Systems that perform tasks normally requiring human judgement, such as perception, language understanding, planning and decision support."),
    Concept("machine_learning", "Machine Learning", "technology",
            ("machine learning", "maskininlärning", "deep learning", "neural network*", "inference service*", "model training", "ai inference", "inference"),
            1.0, area="Digital & AI",
            description="Statistical models that learn patterns from data to predict, classify or optimise, e.g. forecasting, anomaly detection and surrogate models."),
    Concept("computer_vision", "Computer Vision", "technology",
            ("computer vision", "image analysis", "bildanalys", "object detection", "3d vision", "machine vision", "camera-based"),
            1.0, area="Digital & AI",
            description="Algorithms that extract information from images and video, used for inspection, tracking, measurement and surveillance."),
    Concept("edge_ai", "Edge AI", "technology",
            ("edge ai", "edge computing", "on-device", "embedded ai", "tinyml", "edge-to-cloud", "edge cloud"),
            1.0, area="Digital & AI",
            description="Running AI models close to where data is produced (devices, gateways, vessels) to reduce latency, bandwidth and dependency on connectivity."),
    Concept("data_analytics", "Data Analytics", "technology",
            ("data analytics", "analytics", "big data", "dataanalys", "data-driven", "datadriven*", "predictive maintenance", "data platform*", "data spaces", "open data"),
            0.8, area="Digital & AI",
            description="Collecting, processing and analysing operational data to support decisions, optimisation and performance monitoring."),
    Concept("digital_twins", "Digital Twins", "technology",
            ("digital twin*", "digital tvilling*", "digitala tvillingar", "virtual commissioning", "virtual prototyp*", "cyber-physical", "cyberfysiska"),
            1.0, area="Digital & AI",
            description="Continuously updated virtual models of physical assets or processes, used for simulation, monitoring, and what-if analysis."),
    Concept("iot", "Internet of Things", "technology",
            ("internet of things", "CS:IoT", "connected devices", "sensor*", "sakernas internet", "uppkopplade", "remote monitoring"),
            0.8, area="Connectivity & Infrastructure",
            description="Networked sensors and devices that capture and transmit data about physical environments and equipment."),
    Concept("industrial_iot", "Industrial IoT", "technology",
            ("industrial iot", "CS:IIoT", "industry 4.0", "industri 4.0", "condition monitoring", "tillståndsövervakning", "smart factory", "operational technology", "CS:OT security"),
            1.0, area="Connectivity & Infrastructure",
            description="IoT applied to industrial assets and production: condition monitoring, process data, and integration of operational technology with IT."),
    Concept("cloud_computing", "Cloud Computing", "technology",
            ("cloud*", "moln*", "CS:IaaS", "CS:PaaS", "openstack", "kubernetes", "data cent(?:er|re)s?", "datacenter", "high performance computing", "CS:HPC", "eurohpc", "supercomput*"),
            0.9, area="Connectivity & Infrastructure",
            description="On-demand compute, storage and platform services delivered over the network, from public and private clouds to high-performance computing."),
    Concept("cybersecurity", "Cybersecurity", "technology",
            ("cyber(?![\\s-]*(?:physical|fysisk))[\\wåäö]*", "cybersäkerhet*", "information security", "informationssäkerhet", "CS:ISO 27001", "ISO 27001:2022", "digital resilience", "cyber threat*", "säkerhet i digitala", "cybersäkert"),
            1.0, area="Connectivity & Infrastructure",
            description="Protecting systems, networks and data against attack, disruption and unauthorised access, including operational technology and supply-chain security."),
    Concept("connectivity_5g_6g", "5G and 6G", "technology",
            ("CS:5G", "CS:6G", "mobile network*", "radio access", "wireless communication", "trådlös*", "telecommunication*"),
            1.0, area="Connectivity & Infrastructure",
            description="Next-generation mobile networks offering low latency, high reliability and massive device connectivity for industrial and critical uses."),
    Concept("semiconductors_electronics", "Semiconductors & Electronics", "technology",
            ("semiconductor*", "halvledar*", "chips ju", "CS:Chips", "electronic components", "electronic systems", "electronics systems", "elektronik*", "pilot lines"),
            1.0, area="Connectivity & Infrastructure",
            description="Chips, power semiconductors and electronic systems, including design, pilot-line production and validation."),
    Concept("renewable_energy", "Renewable Energy", "technology",
            ("renewable*", "förnybar*", "wave energy", "wave power", "vågkraft", "wind power", "offshore wind", "vindkraft*", "solar", "solenergi", "tidal", "hydrogen", "vätgas", "clean energy", "green electricity", "net-zero", "net zero"),
            1.0, area="Energy & Climate",
            description="Electricity and fuels from renewable resources such as wind, wave, tidal, solar and green hydrogen."),
    Concept("energy_systems", "Energy Systems & Storage", "technology",
            ("energy storage", "energilagring", "batter(?:y|ies)", "batteri*", "flywheel*", "power grid", "electricity grid", "elnät*", "energy flexibility", "flexible energy", "flexibel energi*", "energy efficiency", "energieffektiv*", "power electronics", "inverter*", "CS:HVDC", "substation*", "electricity use", "elanvändning*", "smart ?grids?", "grid balance", "energistyrning"),
            1.0, area="Energy & Climate",
            description="Technologies that store, convert, transmit and flexibly manage electricity: storage, power electronics, grids and demand flexibility."),
    Concept("marine_technology", "Marine Technology", "technology",
            ("marine", "maritime", "marin*", "ocean*", "offshore", "subsea", "underwater", "havs*", "sjöövervakning", "vessel*", "fartyg*", "ship*", "buoy*", "mooring", "sea trial*", "blue economy", "kustbevakning*"),
            0.9, area="Energy & Climate",
            description="Engineering for the sea: offshore structures, vessels, subsea systems, maritime surveillance and ocean energy."),
    Concept("robotics", "Robotics & Autonomy", "technology",
            ("robot*", "robotik", "autonomous", "autonoma", "drone*", "drönare", "industrial automation", "industriell automation", "unmanned"),
            0.9, area="Industrial & Materials",
            description="Machines that sense and act with varying autonomy, from industrial automation to autonomous vessels and inspection drones."),
    Concept("sustainable_manufacturing", "Sustainable Manufacturing", "technology",
            ("sustainable manufacturing", "circular*", "cirkulär*", "hållbar produktion", "low-carbon manufacturing", "life cycle", "lifecycle", "environmental product data", "environmental product declaration*", "CS:EPD*", "net zero industry", "resource efficiency", "remanufactur*", "advanced manufacturing", "production engineering"),
            0.8, area="Industrial & Materials",
            description="Production methods that cut material, energy and emissions across the product life cycle, including circular design and environmental product data."),
    Concept("advanced_materials", "Advanced Materials", "technology",
            ("advanced materials", "material science", "materialteknik", "high performance concrete", "concrete", "betong", "composite*", "kompositer", "polymer*", "rubber", "gummi", "stainless steel", "metallic materials", "critical raw materials", "graphene", "metal and minerals"),
            1.0, area="Industrial & Materials",
            description="Engineered materials with improved properties (strength, durability, weight, conductivity) such as high-performance concrete, polymers and specialty metals."),
)

# --------------------------------------------------------------------------------------------
# Industries / domains
# --------------------------------------------------------------------------------------------
DOMAINS: tuple[Concept, ...] = (
    Concept("energy_sector", "Energy", "domain",
            ("energy", "energi*", "electricity", "power generation", "utilit(?:y|ies)", "power plant*", "kraftnät"), 0.6),
    Concept("maritime_offshore", "Maritime & Offshore", "domain",
            ("maritime", "marine", "offshore", "shipbuild*", "shipping", "sjöfart", "naval", "ocean*", "fartyg*", "marinteknik"), 0.8),
    Concept("manufacturing_industry", "Manufacturing & Process Industry", "domain",
            ("industr(?:y|ies|ial)", "industri*", "manufacturing", "manufactur(?:es|ed|ers?)", "process industr*", "factory", "factories"), 0.5),
    Concept("construction_infrastructure", "Construction & Infrastructure", "domain",
            ("construction", "(?<!digital )(?<!cloud )(?<!secure )infrastructure(?![\\s-]*as[\\s-]+a)", "infrastruktur*", "bygg*", "underground conduit", "tunnel*", "railway*"), 0.6),
    Concept("digital_ict", "ICT & Digital Services", "domain",
            ("software", "mjukvar*", "CS:ICT", "it services", "digitali[sz]ation", "digitalisering", "digital infrastructure", "digital services", "developers"), 0.4),
    Concept("defence_security", "Defence & Security", "domain",
            ("defen[cs]e", "försvar*", "military", "civil preparedness", "beredskap", "national security", "surveillance", "security-cleared"), 0.8),
    Concept("public_sector", "Public Sector", "domain",
            ("public sector", "offentlig sektor", "municipal*", "kommun*", "government", "myndighet*", "public bodies"), 0.6),
    Concept("healthcare_life_science", "Health & Life Science", "domain",
            ("health*", "hälsa", "medtech*", "medical", "life science", "pharma*", "patient*", "vård*", "läkemedel"), 0.9),
    Concept("telecom", "Telecommunications", "domain",
            ("telecom*", "telekom*", "telecom operator*", "mobile operator*"), 0.8),
    Concept("transport_mobility", "Transport & Mobility", "domain",
            ("transport*", "vehicle*", "fordon*", "automotive", "mobility", "CS:FFI"), 0.8),
    Concept("agrifood", "Food & Agriculture", "domain",
            ("food*", "livsmedel*", "agri*", "agtech", "farming", "jordbruk*", "aquaculture"), 0.9),
    Concept("forestry", "Forestry & Bioeconomy", "domain",
            ("forest*", "skog*", "bioeconomy", "bioekonomi"), 0.9),
    Concept("urban_development", "Cities & Urban Development", "domain",
            ("urban", "cit(?:y|ies)", "städer", "stad", "stadsutveckling"), 0.8),
    Concept("creative_industries", "Creative & Cultural Industries", "domain",
            ("creative industr*", "kreativa branscher", "cultural", "kultur*", "konstverk*", "CS:XR", "immersive"), 0.8),
    Concept("finance", "Finance", "domain", ("finance", "banking", "fintech", "finans*"), 0.8),
)

# --------------------------------------------------------------------------------------------
# Capabilities (fine-grained; drive technology adjacency and collaboration complementarity)
# --------------------------------------------------------------------------------------------
CAPABILITIES: tuple[Concept, ...] = (
    Concept("wave_energy_conversion", "Wave energy conversion", "capability",
            ("wave energy converter*", "CS:WEC", "CS:WECs", "wave energy", "wave power", "vågkraft*", "point absorb*", "wave farm*"),
            1.0, implies=("renewable_energy", "marine_technology", "energy_sector", "maritime_offshore")),
    Concept("offshore_structures", "Offshore & subsea structures", "capability",
            ("buoy*", "mooring*", "anchor*", "offshore structure*", "floating structure*", "floating foundation*", "monopile*", "subsea", "hull*", "installation depth", "turbine foundation*", "offshore applications", "decks? and walls"),
            1.0, implies=("marine_technology", "maritime_offshore")),
    Concept("power_takeoff_mechatronics", "Power take-off & mechatronics", "capability",
            ("power take-off", "CS:PTO", "ball screw*", "hydraulic*", "actuat(?:or|ion)*", "generator*", "mechatronic*", "hydrostatic"),
            1.0),
    Concept("control_algorithms", "Advanced control systems", "capability",
            ("model predictive control", "model-based predictive control", "CS:MPC", "control system*", "control algorithm*", "styrsystem", "reglerteknik"),
            1.0),
    Concept("simulation_modelling", "Simulation & modelling", "capability",
            ("simulation*", "simulering*", "numerical model*", "modell?ing", "simulation driven"),
            0.9),
    Concept("prototype_validation", "Prototype validation & sea trials", "capability",
            ("prototype*", "validated", "validation", "sea trials?", "test-rig", "test rig", "scale 1:\\d", "pilot install*", "full scale"),
            0.8),
    Concept("grid_integration", "Grid integration & power electronics", "capability",
            ("grid balance", "power electronics", "inverter*", "flywheel*", "solid state transformer*", "grid connection", "CS:HVDC", "substation*", "converter station*", "transformer room*"),
            1.0, implies=("energy_systems",)),
    Concept("high_performance_concrete", "High-performance concrete structures", "capability",
            ("high performance concrete", "high-performance concrete", "concrete", "betong", "honeycomb"),
            1.0, implies=("advanced_materials",)),
    Concept("cloud_iaas", "Cloud infrastructure (IaaS)", "capability",
            ("infrastructure-as-a-service", "CS:IaaS", "openstack", "public cloud", "private cloud", "compliant cloud", "cloud provider", "virtual machines", "kubernetes", "containers", "cloud computing", "cloud platform"),
            1.0, implies=("cloud_computing", "digital_ict")),
    Concept("data_sovereignty", "Data sovereignty & compliance", "capability",
            ("data sovereignty", "digital sovereignty", "sovereign*", "data protection", "CS:GDPR", "eu data act", "regulatory compliance", "regulated industries", "extraterritorial"),
            1.0),
    Concept("ai_platform", "AI platform & inference services", "capability",
            ("ai platform", "inference services", "sovereign ai", "ai services", "ai offerings"),
            1.0, implies=("artificial_intelligence", "machine_learning", "cloud_computing")),
    Concept("information_security_mgmt", "Information security management", "capability",
            ("CS:ISO 27001", "ISO 27001:2022", "information security", "CS:ISMS", "security-cleared", "business continuity"),
            1.0, implies=("cybersecurity",)),
    Concept("sealing_systems", "Cable & pipe sealing systems", "capability",
            ("seal", "seals", "sealing*", "cable transit*", "pipe transit*", "pipe penetration*", "multi-cable transit*", "CS:MCT", "multidiameter", "cable entry", "cable entries", "tätning*"),
            1.0),
    Concept("fire_explosion_protection", "Fire, gas & explosion protection", "capability",
            ("fire protection", "fire rated", "fire integrity", "explosion*", "blast testing", "CS:A-60", "CS:IP rated", "passive fire", "protection against fire"),
            1.0),
    Concept("emc_shielding", "Electromagnetic shielding (EMC)", "capability",
            ("electromagnetic*", "CS:EMC", "CS:EMI", "CS:EMP", "shielding", "wiretapping"),
            1.0),
    Concept("engineering_software", "Engineering software & digital tools", "capability",
            ("transit designer", "software suite", "CS:CAD", "CS:BIM", "digital tools", "engineering tool*", "bill of material*", "3d cad", "transit build"),
            1.0, implies=("digital_ict",)),
    Concept("hv_cable_systems", "Power cable systems", "capability",
            ("power cable*", "high-voltage", "CS:HV", "submarine cable*", "cable-laying", "CS:HVDC MI", "525 kv", "cable solutions"),
            1.0, implies=("energy_systems", "energy_sector")),
    Concept("testing_certification", "Testing, inspection & certification services", "capability",
            ("testing, inspection", "inspection, and certification", "inspection, certification", "lab testing", "testing laborator*", "testbädd*", "test bed*", "testmiljö*", "testa marinteknik", "assurance, testing"),
            1.0),
    Concept("certified_products", "Certified safety products", "capability",
            ("certified protection", "classification societies", "tests and certifications", "approved by", "certificates", "most tested and certified"),
            0.8),
    Concept("academic_research", "Academic research & education", "capability",
            ("university", "universitet*", "högskola*", "research areas", "researchers", "forskare", "phd", "master’s programme", "master's programme", "institute of technology"),
            1.0),
    Concept("cybersecurity_services", "Cybersecurity services", "capability",
            ("cybersecurity services", "cybersecurity services provider", "secure operational technology", "detect & respond", "CS:CREST", "threat landscape", "penetration test*"),
            1.0, implies=("cybersecurity",)),
    Concept("sustainability_reporting", "Sustainability performance & reporting", "capability",
            ("ecovadis", "CS:CDP", "sustainability report*", "environmental product data", "science based target*", "net-zero emissions"),
            0.8, implies=("sustainable_manufacturing",)),
)

ALL_CONCEPTS: dict[str, Concept] = {c.key: c for c in (*TECHNOLOGIES, *DOMAINS, *CAPABILITIES)}
TECHNOLOGY_KEYS: tuple[str, ...] = tuple(c.key for c in TECHNOLOGIES)
DOMAIN_KEYS: tuple[str, ...] = tuple(c.key for c in DOMAINS)
CAPABILITY_KEYS: tuple[str, ...] = tuple(c.key for c in CAPABILITIES)


@dataclass(frozen=True)
class Adjacency:
    """Capability -> technology relationship with an authored application hypothesis."""

    capability: str
    technology: str
    rationale: str
    application: str
    benefit: str


# Technology adjacency: why a technology may matter to an organisation holding a capability.
# These are authored hypotheses and are always labelled as such.
ADJACENCIES: tuple[Adjacency, ...] = (
    Adjacency("control_algorithms", "digital_twins",
              "Model-based control already depends on an accurate system model.",
              "Extend the control model into a digital twin used for virtual commissioning and fleet performance monitoring.",
              "Shorter validation cycles and earlier detection of performance deviations."),
    Adjacency("control_algorithms", "machine_learning",
              "Predictive control benefits from accurate short-term forecasts of the inputs it reacts to.",
              "Use learned forecasting or estimation models alongside the existing model-based controller.",
              "Potentially higher energy capture or efficiency through better input prediction."),
    Adjacency("control_algorithms", "edge_ai",
              "Real-time control runs on embedded hardware close to the physical process.",
              "Run lightweight estimation or anomaly-detection models on the controller hardware itself.",
              "Lower latency and continued operation without a reliable network link."),
    Adjacency("simulation_modelling", "digital_twins",
              "Simulation-driven development produces models that can be reused as a digital twin.",
              "Connect simulation models to measured prototype data to build a calibrated digital twin.",
              "Better design decisions and evidence for investors and certifiers."),
    Adjacency("simulation_modelling", "cloud_computing",
              "Large simulation campaigns are compute-intensive.",
              "Run parameter sweeps and design optimisation on elastic or high-performance compute.",
              "Faster design iterations without owning compute hardware."),
    Adjacency("offshore_structures", "industrial_iot",
              "Offshore structures are difficult and costly to access for inspection.",
              "Condition monitoring of moorings, structures and seals with remote sensors.",
              "Fewer offshore inspection trips and earlier warning of degradation."),
    Adjacency("offshore_structures", "robotics",
              "Inspection and maintenance at sea is a recognised use case for autonomous systems.",
              "Evaluate autonomous or remotely operated inspection of offshore units.",
              "Reduced operations and maintenance cost over the asset lifetime."),
    Adjacency("offshore_structures", "marine_technology",
              "The organisation already designs structures for the marine environment.",
              "Benchmark against marine test sites and maritime standards relevant to the structure.",
              "De-risked qualification for sea trials and commercial deployment."),
    Adjacency("prototype_validation", "digital_twins",
              "Prototype and sea-trial data can calibrate virtual models.",
              "Use trial data to validate a digital twin before scaling to full size.",
              "Fewer physical test iterations at larger scales."),
    Adjacency("grid_integration", "energy_systems",
              "The organisation works with power conversion, storage or grid connection.",
              "Explore storage and flexibility services that increase the value of delivered electricity.",
              "Additional revenue streams from grid services and smoother power output."),
    Adjacency("power_takeoff_mechatronics", "semiconductors_electronics",
              "Power take-off systems depend on power electronics and drives.",
              "Track wide-bandgap (e.g. SiC) power electronics developments for converters and drives.",
              "Higher conversion efficiency and smaller, lighter power electronics."),
    Adjacency("high_performance_concrete", "advanced_materials",
              "High-performance concrete is itself an advanced material system.",
              "Investigate material durability research and low-carbon binders for marine concrete.",
              "Longer service life and lower embodied carbon per unit."),
    Adjacency("high_performance_concrete", "sustainable_manufacturing",
              "Concrete structures can be produced locally with locally sourced raw materials.",
              "Document life-cycle emissions of local production to strengthen sustainability claims.",
              "Stronger environmental case in tenders and funding applications."),
    Adjacency("cloud_iaas", "edge_ai",
              "Cloud infrastructure providers increasingly extend services towards the edge.",
              "Assess an edge-to-cloud offering for industrial customers with on-site data requirements.",
              "Access to industrial customers who cannot move all data to a central cloud."),
    Adjacency("cloud_iaas", "data_analytics",
              "Customers hosting operational data need analytics services close to the data.",
              "Offer managed data and analytics building blocks on the existing platform.",
              "Higher value per customer and stronger lock-in through services, not contracts."),
    Adjacency("cloud_iaas", "cybersecurity",
              "Cloud infrastructure is a high-value target and security is part of the product.",
              "Strengthen security services (detection, resilience) as part of the cloud offering.",
              "Differentiation in regulated and defence-related markets."),
    Adjacency("ai_platform", "machine_learning",
              "An inference platform hosts machine-learning models for customers.",
              "Package model hosting, fine-tuning and evaluation services for regulated sectors.",
              "Recurring revenue from AI workloads that must stay in the EU."),
    Adjacency("ai_platform", "artificial_intelligence",
              "The organisation is building AI services for customers.",
              "Develop reference AI use cases with industrial or public-sector partners.",
              "Faster adoption of the AI platform through proven use cases."),
    Adjacency("data_sovereignty", "cybersecurity",
              "Sovereignty and compliance are closely tied to security assurance.",
              "Align services with cybersecurity regulation and certification demands of customers.",
              "Easier procurement by regulated and public-sector customers."),
    Adjacency("information_security_mgmt", "cybersecurity",
              "An ISO 27001 management system is a foundation for broader cyber resilience work.",
              "Extend from management-system compliance to industrial cyber resilience services.",
              "New service offerings for industrial customers."),
    Adjacency("sealing_systems", "advanced_materials",
              "Seal performance depends on elastomer and metal material properties.",
              "Follow materials research on elastomer ageing and corrosion resistance in harsh environments.",
              "Longer service life and stronger performance claims in extreme environments."),
    Adjacency("sealing_systems", "industrial_iot",
              "Seals are safety-critical components whose condition is normally verified manually.",
              "Explore whether transit status documentation could be linked to sensor-based condition monitoring.",
              "Potential new digital service around seal lifecycle and inspection."),
    Adjacency("engineering_software", "digital_twins",
              "Engineering tools already hold structured design and installation data for each transit.",
              "Integrate transit data into customers' asset digital twins and BIM workflows.",
              "Stickier software ecosystem and data-driven aftermarket services."),
    Adjacency("engineering_software", "cloud_computing",
              "Web-based engineering tools serving many users run on cloud infrastructure.",
              "Review hosting, data-residency and resilience requirements of the software suite.",
              "Lower operational risk and easier compliance for customers in regulated sectors."),
    Adjacency("emc_shielding", "cybersecurity",
              "Electromagnetic shielding can prevent signal leakage from sensitive areas.",
              "Position shielding solutions for secure facilities such as data centres and defence sites.",
              "Access to security-driven infrastructure markets."),
    Adjacency("emc_shielding", "connectivity_5g_6g",
              "Dense radio infrastructure raises electromagnetic compatibility demands.",
              "Assess EMC sealing needs in telecom and 5G infrastructure sites.",
              "New application segment for existing shielding products."),
    Adjacency("fire_explosion_protection", "renewable_energy",
              "Energy installations such as offshore substations require certified fire and gas protection.",
              "Target renewable-energy installations where certified protection is mandatory.",
              "Growth aligned with the expansion of offshore wind and grid infrastructure."),
    Adjacency("sustainability_reporting", "sustainable_manufacturing",
              "The organisation already reports environmental performance and product data.",
              "Use environmental product data to support circular design and low-carbon manufacturing projects.",
              "Stronger position where buyers require documented environmental performance."),
    Adjacency("hv_cable_systems", "renewable_energy",
              "Power cables connect renewable generation to the grid.",
              "Export and array cabling for offshore renewable installations.",
              "Participation in the build-out of offshore renewables."),
    Adjacency("academic_research", "artificial_intelligence",
              "University research groups develop and apply AI methods.",
              "Joint research projects and student theses on applied AI problems.",
              "Access to research competence and talent."),
)

# Industry-level technology relevance (weaker than capability adjacency).
DOMAIN_TECH: dict[str, tuple[str, ...]] = {
    "energy_sector": ("renewable_energy", "energy_systems", "data_analytics", "industrial_iot"),
    "maritime_offshore": ("marine_technology", "robotics", "iot", "advanced_materials"),
    "manufacturing_industry": ("industrial_iot", "sustainable_manufacturing", "robotics", "digital_twins", "advanced_materials"),
    "construction_infrastructure": ("digital_twins", "advanced_materials", "sustainable_manufacturing"),
    "digital_ict": ("cloud_computing", "cybersecurity", "artificial_intelligence", "data_analytics", "edge_ai"),
    "defence_security": ("cybersecurity", "computer_vision", "connectivity_5g_6g"),
    "public_sector": ("cloud_computing", "cybersecurity", "artificial_intelligence"),
    "telecom": ("connectivity_5g_6g", "edge_ai"),
    "healthcare_life_science": ("artificial_intelligence", "data_analytics"),
}

# --------------------------------------------------------------------------------------------
# Complementarity rules for collaboration discovery (need on one side, offer on the other)
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class ComplementarityRule:
    key: str
    need: tuple[str, ...]  # any of these capabilities/domains on the seeking side
    offer: tuple[str, ...]  # any of these on the providing side
    relation: str  # component_supply | testing_validation | research | digital_infrastructure | security | market_access
    strength: float
    rationale: str  # uses {seeker}, {provider}, {need_label}, {offer_label}
    scenario: str
    seeker_benefit: str
    provider_benefit: str
    first_step: str
    priority_key: str | None = None  # company priority that amplifies this rule
    tags: tuple[str, ...] = field(default=())


COMPLEMENTARITY_RULES: tuple[ComplementarityRule, ...] = (
    ComplementarityRule(
        "offshore_sealing", ("offshore_structures", "wave_energy_conversion"), ("sealing_systems",), "component_supply", 1.0,
        "{seeker} documents {need_label} that must operate in harsh marine conditions; {provider} documents {offer_label} for marine and offshore installations.",
        "Technical workshop to assess cable and pipe penetration sealing requirements in {seeker}'s offshore units, using {provider}'s published offshore sealing range as a starting point.",
        "Access to proven, certified sealing know-how for marine environments, potentially de-risking sea trials.",
        "A reference application in an emerging offshore renewable segment.",
        "Request a technical scoping call with {provider}'s marine/offshore application engineers about penetrations in the next prototype.",
        priority_key="improve_products"),
    ComplementarityRule(
        "renewables_grid_cable", ("wave_energy_conversion", "grid_integration"), ("hv_cable_systems",), "component_supply", 0.8,
        "{seeker} works on {need_label}; {provider} documents {offer_label} used to connect generation to the grid.",
        "Early dialogue on export and array cable requirements for {seeker}'s planned multi-unit installations.",
        "Earlier insight into grid-connection cost and design constraints.",
        "Visibility of an emerging offshore generation technology and future cable demand.",
        "Prepare a one-page summary of expected array layout and power levels and ask {provider} for an informal requirements discussion.",
        priority_key="improve_products"),
    ComplementarityRule(
        "validation_testing", ("prototype_validation", "certified_products"), ("testing_certification",), "testing_validation", 1.0,
        "{seeker} relies on {need_label}; {provider} documents {offer_label}.",
        "Map {seeker}'s upcoming validation and certification steps against {provider}'s testing and inspection services.",
        "Independent testing and verification that can strengthen credibility with customers and funders.",
        "A defined testing and certification assignment in a growth segment.",
        "List the next three validation milestones and ask {provider} which can be covered by their testing or inspection services.",
        priority_key="testing_facilities"),
    ComplementarityRule(
        "research_partnership_control", ("control_algorithms", "simulation_modelling"), ("academic_research",), "research", 0.8,
        "{seeker} develops {need_label}; {provider} conducts {offer_label} in areas such as computer science, mechanical engineering and systems engineering.",
        "A joint research project or master's thesis on modelling, control or optimisation problems from {seeker}'s development work.",
        "Research capacity and access to students and methods without full-time hires.",
        "Industrially relevant research problems and data.",
        "Contact {provider}'s relevant research area to discuss a thesis or a joint application to an open research call.",
        priority_key="research_collaboration"),
    ComplementarityRule(
        "research_partnership_digital", ("ai_platform", "engineering_software", "cloud_iaas"), ("academic_research",), "research", 0.7,
        "{seeker} offers {need_label}; {provider} conducts {offer_label} including computer science and software engineering.",
        "Joint applied research on secure, efficient or trustworthy software and AI services.",
        "Research-backed product development and access to talent.",
        "Industrial infrastructure and real-world problems for research.",
        "Identify one research question and approach {provider}'s computer science or software engineering group.",
        priority_key="research_collaboration"),
    ComplementarityRule(
        "research_partnership_product", ("sealing_systems", "fire_explosion_protection", "high_performance_concrete"), ("academic_research",), "research", 0.6,
        "{seeker} develops {need_label}; {provider} conducts {offer_label}, including mechanical engineering and digital product development.",
        "Applied research on product development methods, materials behaviour or simulation for {seeker}'s products.",
        "Research input into product development.",
        "Industrial collaboration and research data.",
        "Discuss a thesis or joint project with {provider}'s mechanical engineering research area.",
        priority_key="research_collaboration"),
    ComplementarityRule(
        "sovereign_hosting", ("engineering_software", "simulation_modelling"), ("cloud_iaas", "data_sovereignty"), "digital_infrastructure", 0.5,
        "{seeker} operates {need_label} that need compute and hosting; {provider} documents {offer_label}.",
        "Evaluate EU-hosted infrastructure for {seeker}'s digital tools or compute-intensive workloads.",
        "European-hosted infrastructure with documented compliance certifications.",
        "An industrial reference customer with engineering workloads.",
        "Run a small proof-of-concept workload on {provider}'s platform and compare cost, performance and compliance.",
        priority_key="new_technology"),
    ComplementarityRule(
        "cloud_security_services", ("cloud_iaas", "data_sovereignty"), ("cybersecurity_services",), "security", 0.7,
        "{seeker} provides {need_label}; {provider} provides {offer_label}.",
        "Combined offering of compliant infrastructure and security services for regulated customers.",
        "Stronger security proposition for regulated and defence customers.",
        "A compliant hosting partner for security-sensitive clients.",
        "Explore a joint offering for one regulated customer segment, e.g. public sector or defence suppliers.",
        priority_key="new_industries"),
    ComplementarityRule(
        "shielded_infrastructure", ("data_sovereignty", "information_security_mgmt"), ("emc_shielding",), "security", 0.4,
        "{seeker} emphasises {need_label}; {provider} documents {offer_label}, which its own material describes as protecting sensitive information from wiretapping.",
        "Exploratory review of whether electromagnetic shielding is relevant for security-classified hosting environments.",
        "An additional physical-security layer for high-assurance environments.",
        "A potential new application segment (secure data facilities).",
        "Treat as exploratory: ask whether high-assurance customers have shielding requirements before investing time.",
        priority_key="new_industries"),
    ComplementarityRule(
        "ot_security_offshore", ("control_algorithms", "grid_integration", "engineering_software"), ("cybersecurity_services",), "security", 0.4,
        "{seeker} develops {need_label} that are becoming connected; {provider} documents {offer_label} including operational technology.",
        "Exploratory review of cyber risks in connected control or engineering systems.",
        "Security-by-design input before commercial deployment.",
        "Early engagement in an emerging industrial segment.",
        "Ask {provider} for a short threat-modelling session on the connected parts of the system.",
        priority_key="improve_products"),
    ComplementarityRule(
        "hv_sealing", ("hv_cable_systems", "grid_integration"), ("sealing_systems", "fire_explosion_protection"), "component_supply", 0.6,
        "{seeker} works with {need_label}; {provider} documents {offer_label} for energy installations.",
        "Coordinate cable entry and penetration sealing specifications for energy installations.",
        "Certified protection at cable entries.",
        "Specification in energy-infrastructure projects.",
        "Compare cable entry requirements in a current project with {provider}'s documented energy-sector solutions.",
        priority_key="improve_products"),
)

# --------------------------------------------------------------------------------------------
# Company priorities a representative can set
# --------------------------------------------------------------------------------------------
PRIORITIES: dict[str, dict[str, str]] = {
    "find_funding": {"label": "Find new funding", "description": "Grants, innovation and research funding calls."},
    "research_collaboration": {"label": "Explore research collaborations", "description": "Universities, research calls and joint projects."},
    "new_technology": {"label": "Discover new technologies", "description": "Emerging technologies adjacent to current capabilities."},
    "new_industries": {"label": "Expand into new industries", "description": "Markets and segments outside today's core."},
    "improve_products": {"label": "Improve product capabilities", "description": "Components, partners and technology for existing products."},
    "testing_facilities": {"label": "Find testing facilities", "description": "Test beds, labs, validation and certification."},
    "regional_focus": {"label": "Prefer the local Blekinge ecosystem", "description": "Weight nearby events, facilities and partners higher (never replaces relevance)."},
}
DEFAULT_PRIORITY_WEIGHT = 1

# How much each priority amplifies each opportunity category (0..1)
PRIORITY_CATEGORY_AFFINITY: dict[str, dict[str, float]] = {
    "find_funding": {"funding_call": 1.0, "research_funding": 0.8, "innovation_programme": 0.9, "research_collaboration": 0.6, "business_programme": 0.5},
    "research_collaboration": {"research_funding": 1.0, "research_collaboration": 1.0, "innovation_programme": 0.4},
    "new_technology": {"event": 0.6, "innovation_programme": 0.5, "research_funding": 0.4, "testing_facility": 0.4},
    "new_industries": {"event": 0.7, "business_programme": 0.8, "innovation_programme": 0.4},
    "improve_products": {"innovation_programme": 0.7, "funding_call": 0.5, "testing_facility": 0.6},
    "testing_facilities": {"testing_facility": 1.0, "research_collaboration": 0.3},
}
