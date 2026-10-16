"""Fetch article pages safely and pull out the readable text."""

import ipaddress
import logging
import socket
from urllib.parse import urljoin, urlparse

import requests
import trafilatura

from .news import UNSUMMARIZABLE_HOSTS

log = logging.getLogger(__name__)

MAX_BYTES = 4 * 1024 * 1024
MAX_REDIRECTS = 5
TIMEOUT = (5, 12)
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/141.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.5",
    "Accept-Language": "en-US,en;q=0.9",
}


class ExtractionError(Exception):
    """The article couldn't be fetched or read. `message` is safe to show to users."""

    def __init__(self, code, message, status=422):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def _resolve_is_public(host, port):
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0].split("%")[0])
        if getattr(ip, "ipv4_mapped", None):
            ip = ip.ipv4_mapped
        if not ip.is_global or ip.is_multicast:
            return False
    return bool(infos)


def validate_public_url(url):
    """Reject anything that could make the server fetch internal resources (SSRF)."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ExtractionError("invalid_url", "That link isn't a web address we can open.", 400)
    if parsed.username or parsed.password:
        raise ExtractionError("invalid_url", "Links with credentials aren't supported.", 400)
    if parsed.port not in (None, 80, 443):
        raise ExtractionError("invalid_url", "That link uses a port we don't open.", 400)

    host = parsed.hostname.lower()
    if host in UNSUMMARIZABLE_HOSTS:
        raise ExtractionError(
            "unsupported_source",
            "This story is behind an aggregator link we can't open. Read it on the publisher's site.",
        )
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        raise ExtractionError("invalid_url", "That link points to a private address.", 400)
    if not _resolve_is_public(host, parsed.port or (443 if parsed.scheme == "https" else 80)):
        raise ExtractionError("invalid_url", "That link points to a private or unknown address.", 400)


def fetch_html(url, session=None):
    """GET a page, following redirects manually so every hop is validated, with a size cap."""
    session = session or requests.Session()
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        validate_public_url(current)
        try:
            response = session.get(
                current, headers=BROWSER_HEADERS, timeout=TIMEOUT, stream=True, allow_redirects=False
            )
        except requests.Timeout as exc:
            raise ExtractionError("fetch_timeout", "The publisher's site took too long to respond.", 504) from exc
        except requests.RequestException as exc:
            raise ExtractionError("fetch_failed", "We couldn't reach the publisher's site.", 502) from exc

        with response:
            if response.is_redirect:
                location = response.headers.get("Location")
                if not location:
                    break
                current = urljoin(current, location)
                continue

            if response.status_code in (401, 402, 403, 451):
                raise ExtractionError(
                    "blocked", "The publisher blocks automated reading (often a paywall)."
                )
            if response.status_code >= 400:
                raise ExtractionError(
                    "fetch_failed", f"The publisher's site returned an error ({response.status_code})."
                )

            content_type = response.headers.get("Content-Type", "").lower()
            if content_type and "html" not in content_type:
                raise ExtractionError("not_html", "That link isn't an article page.")

            body = bytearray()
            for chunk in response.iter_content(64 * 1024):
                body.extend(chunk)
                if len(body) > MAX_BYTES:
                    raise ExtractionError("too_large", "That page is too large to summarize.")
            return current, bytes(body)

    raise ExtractionError("too_many_redirects", "That link redirects too many times.")


def extract_article(url, session=None):
    final_url, body = fetch_html(url, session=session)
    try:
        doc = trafilatura.bare_extraction(
            body,
            url=final_url,
            with_metadata=True,
            include_comments=False,
            include_tables=False,
            favor_precision=True,
            as_dict=True,
        )
    except Exception as exc:  # trafilatura can raise on badly broken markup
        log.warning("extraction crashed for %s: %s", final_url, exc)
        doc = None

    text = (doc or {}).get("text") or ""
    words = len(text.split())
    if words < 80:
        raise ExtractionError(
            "no_content",
            "We couldn't find enough article text on that page (it may be a video, gallery, or paywall).",
        )

    return {
        "url": final_url,
        "title": doc.get("title"),
        "author": doc.get("author"),
        "publishedAt": doc.get("date"),
        "image": doc.get("image"),
        "siteName": doc.get("sitename"),
        "text": text,
        "wordCount": words,
    }
