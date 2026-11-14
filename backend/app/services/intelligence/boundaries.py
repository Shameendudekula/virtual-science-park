"""Service boundaries for free-text questions ("Ask VSP"). Deterministic rules only — no LLM is involved.

Every request is classified on its own, before any search runs, so the same rules apply to first questions and
follow-ups alike (the service keeps no conversation state that a later message could re-instruct).

Categories, checked in this order (the first match wins):
  override       attempts to change the service's role or rules, or to reveal its configuration   -> declined
  private_data   requests for non-public company data, conversations, credentials                  -> declined
  eligibility    "are we eligible / will we get funding?"                                           -> answered with a notice
  needs_human    decisions, commitments or professional advice only a person can give              -> referred to staff
  out_of_scope   anything outside innovation, funding, technology, testing, collaboration, business -> declined
  in_scope       everything else that mentions a supported topic                                    -> answered

Messages are fixed text and never echo the user's input, so nothing in a question can be reflected back as an answer.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

REMIT = ("Virtual Science Park helps companies in the Blue Science Park ecosystem find funding, testing environments, "
         "events, technologies and potential collaboration partners.")
SUGGESTIONS = [
    "Which funding opportunities are relevant to my company?",
    "Which companies have complementary expertise in marine technology?",
    "Which testing facilities could help validate our technology?",
]
# The organisation's official public website; no personal or unverified contact details are stated.
STAFF_REFERRAL = {"label": "Contact Blue Science Park staff via the official website", "url": "https://www.bluesciencepark.se/"}


def _rx(*patterns: str) -> re.Pattern[str]:
    return re.compile("|".join(f"(?:{p})" for p in patterns), re.I)


OVERRIDE = _rx(
    r"\b(ignore|disregard|forget|override|bypass)\s+((all|any|the|your|my|these|those|previous|prior|above|earlier|system|safety|of|its)\s+)*"
    r"(instructions?|rules?|prompts?|guidelines|guardrails|restrictions|programming|polic(y|ies))\b",
    r"\b(ignore|disregard|forget)\s+(everything|all|anything)\s+(above|before|earlier|previous\w*|prior|you\s+were\s+told)\b",
    r"\bunrestricted\s+(assistant|ai|mode|model|chatbot|bot)\b",
    r"\b(system|hidden|initial|internal)\s+(prompt|instructions?|message|rules)\b",
    r"\b(reveal|show|print|repeat|output|leak|display)\b.{0,30}\b(your|the)\s+(prompt|instructions?|rules|configuration|config)\b",
    r"\byou\s+are\s+(now|no\s+longer)\b",
    r"\b(act|behave|respond)\s+as\s+(an?\s+)?(unrestricted|unfiltered|different|new|other|another)\b",
    r"\bpretend\s+(to\s+be|you\s+are|that\s+you)\b",
    r"\b(jailbreak|developer\s+mode|dan\s+mode|god\s+mode)\b",
    r"\bnew\s+(instructions|rules|role)\s*:",
    r"\b(ignorera|strunta\s+i|glöm)\b.{0,40}\b(instruktioner\w*|regler\w*)\b",
    r"\bsystemprompt\w*\b",
)
PRIVATE = _rx(
    r"\b(confidential|secret|non-public|unpublished)\b.{0,30}\b(profiles?|data|information|info|plans?|notes?|conversations?|messages?|history|details|documents?|records?)\b",
    r"\b(private|internal|hidden)\s+(\w+\s+){0,2}(profiles?|plans?|notes?|conversations?|messages?|chats?|history|documents?|records?|workspaces?)\b",
    r"\b(conversations?|chat\s*logs?|chats|messages|question\s+history|search\s+history|saved\s+(items|recommendations))\b.{0,30}\b(of|from|for|by)\b",
    r"\b(another|other|competitor'?s?)\s+compan(y|y's|ies'?)\b.{0,40}\b(profile|data|history|questions|conversations|accounts?)\b",
    r"\b(passwords?|credentials|api\s+keys?|access\s+tokens?|session\s+tokens?|login\s+details)\b",
    r"\b(email\s+addresses|phone\s+numbers|personal\s+data)\s+of\b",
)
ELIGIBILITY = _rx(
    r"\beligib\w*",
    r"\b(qualif(y|ies|ied)|entitled)\b.{0,30}\b(for|to)\b",
    r"\b(guarantee\w*|promise\w*)\b.{0,30}\b(funding|grant|money|financ\w*|award\w*|accepted|approved)\b",
    r"\b(will|would|do|does)\s+(we|i|they|it|my\s+company|this\s+company|our\s+company)\s+(get|receive|win|be\s+(granted|awarded|funded|approved|accepted))\b",
    r"\b(behörig\w*|stödberättigad\w*)\b",
)
NEEDS_HUMAN = _rx(
    r"\b(official|formal|binding|final)\s+(decision|approval|commitment|confirmation|answer|ruling)\b",
    r"\b(legal|tax|financial|investment|accounting)\s+advice\b",
    r"\b(lawyer|attorney|accountant)\b",
    r"\bshould\s+(we|i)\s+(sign|accept|invest|hire|fire|sue)\b",
    r"\b(talk|speak)\s+to\s+(a\s+)?(human|person|someone|staff|advisor|adviser)\b",
    r"\b(contact|call|email|reach)\s+(blue\s+science\s+park|bsp|your\s+staff|a\s+person|someone)\b",
    r"\b(book|schedule|arrange)\s+(a\s+)?(meeting|call|appointment|visit)\b",
    r"\b(apply|sign\s+up|register)\s+on\s+(my|our)\s+behalf\b",
    r"\b(membership|office|desk)\s+(fee|price|cost|rent|contract)\b",
    r"\b(will|can)\s+(blue\s+science\s+park|bsp)\s+(fund|sponsor|invest|approve|commit|guarantee|pay)\b",
)
# Requests that are off-topic even when they mention a supported word ("a poem about funding"). Kept narrow on purpose:
# industries such as games, film or weather services are legitimate business topics and fall through to the topic check.
OFF_TOPIC = _rx(
    r"\b(poems?|poetry|sonnets?|haikus?|limericks?|lyrics|jokes?|riddles?|fairy\s*tales?|bedtime\s+stor(y|ies)|short\s+stor(y|ies))\b",
    r"\b(recipes?|horoscopes?|astrology|dating\s+(advice|tips)|romantic|love\s+letters?)\b",
    r"\b(my\s+homework|school\s+essay)\b",
    r"\b(dikt(er|en)?|recept)\b",
)
IN_SCOPE = _rx(
    r"\b(fund\w*|grants?|financ\w*|calls?|opportunit\w*|programmes?|programs?|deadlines?|apply|applications?|vinnova)\b",
    r"\b(events?|conferences?|workshops?|seminars?|meetups?|webinars?|hackathons?)\b",
    r"\b(test\w*|labs?|laborator\w*|facilit\w*|pilots?|demonstrat\w*|validat\w*|certif\w*)\b",
    r"\b(partners?|partnerships?|collaborat\w*|cooperat\w*|consorti\w*|compan(y|ies)|members?|startups?|suppliers?|customers?)\b",
    r"\b(technolog\w*|tech|innovat\w*|research\w*|r&d|develop\w*|products?|services?|expertise|capabilit\w*|solutions?)\b",
    r"\b(business\w*|markets?|industr\w*|export\w*|commerciali[sz]\w*|scale\w*|growth|investors?)\b",
    r"\b(science\s+park|blue\s+science\s+park|bsp|blekinge|karlskrona|ecosystem)\b",
    r"\b(finansiering|bidrag|utlysning\w*|evenemang|testbädd\w*|samarbet\w*|företag\w*|teknik\w*|forskning\w*|innovation\w*|affär\w*)\b",
)


@dataclass
class Boundary:
    category: str
    handling: str  # answered | answered_with_notice | declined | referred
    message: str | None = None
    suggestions: list[str] = field(default_factory=list)
    referral: dict | None = None

    @property
    def runs_search(self) -> bool:
        return self.handling in ("answered", "answered_with_notice")

    def as_dict(self) -> dict:
        return {"category": self.category, "handling": self.handling, "message": self.message,
                "suggestions": self.suggestions, "referral": self.referral, "classifier": "deterministic rules (no LLM)"}


def normalise(text: str) -> str:
    """NFKC, drop zero-width/control characters and collapse whitespace, so spacing tricks don't hide keywords."""
    text = unicodedata.normalize("NFKC", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) not in ("Cf", "Cc") or ch in "\n\t")
    return re.sub(r"\s+", " ", text).strip()


def _mentions_supported_topic(text: str) -> bool:
    if IN_SCOPE.search(text):
        return True
    from app.services.intelligence.concepts import extract  # taxonomy terms (e.g. "wave energy", "cybersecurity")

    return any(m.direct for m in extract(text).values())


def classify(text: str) -> Boundary:
    t = normalise(text)
    if OVERRIDE.search(t):
        return Boundary("override", "declined",
                        "This service can't change its role or rules, and it doesn't share its internal configuration. " + REMIT,
                        SUGGESTIONS)
    if PRIVATE.search(t):
        return Boundary("private_data", "declined",
                        "Private workspace data, such as a company's unpublished profile details, saved items, questions or "
                        "account details, is never shared through this service. You can ask about public capabilities "
                        "and opportunities instead.", SUGGESTIONS)
    if ELIGIBILITY.search(t):
        return Boundary("eligibility", "answered_with_notice",
                        "These results are potential matches only. VSP does not assess formal eligibility and cannot guarantee "
                        "funding: the funder decides, based on its call text. Check the eligibility requirements on each "
                        "call's source page, and ask the funder or Blue Science Park staff for official guidance.",
                        referral=STAFF_REFERRAL)
    if NEEDS_HUMAN.search(t):
        return Boundary("needs_human", "referred",
                        "This needs a decision, commitment or professional advice from a person, which this service can't "
                        "give. Please contact Blue Science Park staff. " + REMIT, SUGGESTIONS, STAFF_REFERRAL)
    if OFF_TOPIC.search(t) or not _mentions_supported_topic(t):
        return Boundary("out_of_scope", "declined",
                        "That request is outside what this service does. " + REMIT + " Try one of the questions below.",
                        SUGGESTIONS)
    return Boundary("in_scope", "answered")


def declined_response(text: str, boundary: Boundary) -> dict:
    """Search-response shape with no results, so clients render it like any other answer."""
    return {"query": {"text": text, "intent": "none", "company_id": None, "company_name": None, "concepts": [], "categories": [],
                      "notes": [], "parser": "deterministic rules (no LLM)"},
            "results": [], "count": 0, "note": "No search was run for this request.", "boundary": boundary.as_dict()}
