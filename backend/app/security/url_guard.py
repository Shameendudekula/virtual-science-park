"""Outbound URL safety: SSRF protection, host allowlisting, redirect validation and size limits.

Every outbound request made by a collector goes through `SafeHttpClient`. It:
  * only allows https (http is rejected),
  * only allows hosts on the source's allowlist (exact host or subdomain of an allowed host),
  * resolves DNS and rejects private, loopback, link-local, multicast and reserved addresses,
  * follows redirects manually, re-validating every hop (max 5),
  * enforces a timeout and a maximum response size while streaming.
"""
from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

import httpx

from app.core.config import get_settings

MAX_REDIRECTS = 5


class UrlRejected(ValueError):
    """Raised when a URL fails validation. The message is safe to show to administrators."""


def _host_allowed(host: str, allowed_hosts: Iterable[str]) -> bool:
    host = host.lower().rstrip(".")
    for allowed in allowed_hosts:
        allowed = allowed.lower().rstrip(".")
        if host == allowed or host.endswith("." + allowed):
            return True
    return False


def _is_public_ip(ip: str) -> bool:
    addr = ipaddress.ip_address(ip)
    return not (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_reserved
        or addr.is_unspecified
        or (isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None and not _is_public_ip(str(addr.ipv4_mapped)))
    )


Resolver = Callable[[str], list[str]]


def system_resolver(host: str) -> list[str]:
    infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
    return sorted({info[4][0] for info in infos})


def validate_url(url: str, allowed_hosts: Iterable[str], resolver: Resolver | None = system_resolver) -> str:
    """Validate a URL for outbound fetching. Returns the normalised URL or raises UrlRejected."""
    if not isinstance(url, str) or len(url) > 2048:
        raise UrlRejected("URL missing or too long")
    parts = urlsplit(url.strip())
    if parts.scheme != "https":
        raise UrlRejected("Only https URLs are allowed")
    if parts.username or parts.password:
        raise UrlRejected("Credentials in URLs are not allowed")
    host = (parts.hostname or "").lower()
    if not host:
        raise UrlRejected("URL has no host")
    if parts.port not in (None, 443):
        raise UrlRejected("Non-standard ports are not allowed")
    try:
        ipaddress.ip_address(host.strip("[]"))
        is_ip_literal = True
    except ValueError:
        is_ip_literal = False
    if is_ip_literal:
        raise UrlRejected("IP-literal hosts are not allowed")
    if not _host_allowed(host, allowed_hosts):
        raise UrlRejected(f"Host '{host}' is not on the source allowlist")
    if resolver is not None:
        try:
            addresses = resolver(host)
        except OSError as exc:
            raise UrlRejected(f"DNS resolution failed for '{host}'") from exc
        if not addresses:
            raise UrlRejected(f"DNS resolution returned no addresses for '{host}'")
        for ip in addresses:
            if not _is_public_ip(ip):
                raise UrlRejected(f"Host '{host}' resolves to a non-public address")
    return parts.geturl()


@dataclass
class FetchResult:
    url: str
    status_code: int
    content: bytes
    content_type: str

    def json(self):  # noqa: ANN201
        import json

        return json.loads(self.content.decode("utf-8"))

    @property
    def text(self) -> str:
        return self.content.decode("utf-8", errors="replace")


class SafeHttpClient:
    def __init__(
        self,
        allowed_hosts: Iterable[str],
        *,
        transport: httpx.BaseTransport | None = None,
        resolver: Resolver | None = system_resolver,
        timeout: float | None = None,
        max_bytes: int | None = None,
    ) -> None:
        settings = get_settings()
        self.allowed_hosts = list(allowed_hosts)
        self.resolver = resolver
        self.max_bytes = max_bytes or settings.http_max_response_bytes
        self._client = httpx.Client(
            transport=transport,
            timeout=httpx.Timeout(timeout or settings.http_timeout_seconds),
            follow_redirects=False,
            headers={"User-Agent": settings.http_user_agent, "Accept": "application/json, text/html;q=0.9"},
        )

    def __enter__(self) -> SafeHttpClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self._client.close()

    def get(self, url: str, params: dict | None = None) -> FetchResult:
        current = validate_url(url, self.allowed_hosts, self.resolver)
        for _ in range(MAX_REDIRECTS + 1):
            with self._client.stream("GET", current, params=params) as response:
                if response.is_redirect:
                    location = response.headers.get("location", "")
                    current = validate_url(urljoin(current, location), self.allowed_hosts, self.resolver)
                    params = None
                    continue
                declared = response.headers.get("content-length")
                if declared and declared.isdigit() and int(declared) > self.max_bytes:
                    raise UrlRejected("Response exceeds the maximum allowed size")
                chunks: list[bytes] = []
                size = 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > self.max_bytes:
                        raise UrlRejected("Response exceeds the maximum allowed size")
                    chunks.append(chunk)
                response.raise_for_status()
                return FetchResult(str(response.url), response.status_code, b"".join(chunks), response.headers.get("content-type", ""))
        raise UrlRejected("Too many redirects")
