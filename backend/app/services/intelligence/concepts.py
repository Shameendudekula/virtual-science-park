"""Deterministic concept extraction over the VSP knowledge base.

Turns free text (company claims, opportunity descriptions, search queries) into a mapping of
concept key -> matched terms. All matching downstream is concept-based, never raw token overlap.
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache

from app.services.intelligence.taxonomy import ALL_CONCEPTS, Concept

_WORD = r"[\wåäöÅÄÖéü]"


def _compile_term(term: str) -> re.Pattern[str]:
    flags = re.IGNORECASE
    if term.startswith("CS:"):
        term = term[3:]
        flags = 0
    wildcard = term.endswith("*")
    if wildcard:
        term = term[:-1]
    # Terms may contain small regex groups (e.g. 'data cent(?:er|re)s?'); escape everything else.
    if any(ch in term for ch in "()[]?|\\"):
        body = term
    else:
        body = re.escape(term).replace(r"\ ", r"\s+")
    suffix = rf"{_WORD}*" if wildcard else ""
    return re.compile(rf"(?<!{_WORD}){body}{suffix}(?!{_WORD})", flags)


@lru_cache(maxsize=1)
def _compiled() -> dict[str, list[tuple[str, re.Pattern[str]]]]:
    return {key: [(t, _compile_term(t)) for t in c.terms] for key, c in ALL_CONCEPTS.items()}


@dataclass
class ConceptMatch:
    key: str
    terms: list[str]
    direct: bool  # False when only present through another concept's `implies`

    @property
    def concept(self) -> Concept:
        return ALL_CONCEPTS[self.key]


def extract(text: str | None, *, with_implied: bool = True) -> dict[str, ConceptMatch]:
    """Return concept matches found in `text`. Implied concepts are added with direct=False."""
    if not text:
        return {}
    found: dict[str, ConceptMatch] = {}
    for key, patterns in _compiled().items():
        hits: list[str] = []
        for _term, pattern in patterns:
            for m in pattern.finditer(text):
                hit = m.group(0).strip()
                if hit.lower() not in (h.lower() for h in hits):
                    hits.append(hit)
            if len(hits) >= 4:
                break
        if hits:
            found[key] = ConceptMatch(key, hits, True)
    if with_implied:
        for key in list(found):
            for implied in ALL_CONCEPTS[key].implies:
                if implied not in found:
                    found[implied] = ConceptMatch(implied, [f"via {ALL_CONCEPTS[key].label}"], False)
    return found


def extract_keys(text: str | None) -> list[str]:
    return sorted(extract(text).keys())


def merge_texts(parts: Iterable[str | None]) -> str:
    return "\n".join(p for p in parts if p)


def label(key: str) -> str:
    c = ALL_CONCEPTS.get(key)
    return c.label if c else key.replace("_", " ").title()
