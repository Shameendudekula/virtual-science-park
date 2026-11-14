"""Text utilities shared by collectors: HTML to text, normalisation, hashing, sanitising."""
from __future__ import annotations

import hashlib
import html
import re
import unicodedata
from html.parser import HTMLParser

_BLOCK_TAGS = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "div", "br", "section", "article", "tr", "td", "th", "a", "span"}
_SKIP_TAGS = {"script", "style", "noscript", "svg", "template", "iframe"}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
        if tag in _SKIP_TAGS:
            self._skip += 1
        elif tag in _BLOCK_TAGS:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS and self._skip:
            self._skip -= 1
        elif tag in _BLOCK_TAGS:
            self.parts.append(" ")

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.parts.append(data)


def html_to_text(markup: str) -> str:
    parser = _TextExtractor()
    parser.feed(markup)
    return normalise(" ".join(parser.parts))


_QUOTES = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-", " ": " ", "™": ""})


def normalise(text: str) -> str:
    """Normalise for robust excerpt comparison: unicode NFC, quotes/dashes, collapsed whitespace."""
    text = unicodedata.normalize("NFC", html.unescape(text)).translate(_QUOTES)
    text = re.sub(r"\s+", " ", text)
    # Inline markup can leave a space before punctuation ("penetrations ."); remove it.
    text = re.sub(r" ([.,;:!?)])", r"\1", text)
    return text.strip()


def contains_excerpt(page_text: str, excerpt: str) -> bool:
    return normalise(excerpt).lower() in normalise(page_text).lower()


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


_TAG_RE = re.compile(r"<[^>]+>")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def clean_field(value: object, max_len: int = 4000) -> str | None:
    """Sanitise an untrusted string field from an external source.

    Strips markup and control characters and truncates. The result is stored and displayed as
    inert text; it is never interpreted as an instruction by any part of the system.
    """
    if value is None:
        return None
    text = html.unescape(_TAG_RE.sub(" ", str(value)))
    text = _CONTROL_RE.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return None
    return text[:max_len]
