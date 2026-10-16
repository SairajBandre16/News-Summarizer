import socket

import pytest

from blitzfeed import extract
from blitzfeed.extract import ExtractionError, fetch_html, validate_public_url


def _fake_resolver(mapping):
    def getaddrinfo(host, port, type=0):
        if host not in mapping:
            raise socket.gaierror("unknown host")
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (mapping[host], port))]

    return getaddrinfo


@pytest.fixture
def resolver(monkeypatch):
    mapping = {
        "public.example": "93.184.216.34",
        "internal.example": "10.0.0.5",
        "metadata.example": "169.254.169.254",
        "loopback.example": "127.0.0.1",
    }
    monkeypatch.setattr(extract.socket, "getaddrinfo", _fake_resolver(mapping))
    return mapping


@pytest.mark.parametrize(
    "url",
    [
        "ftp://public.example/file",
        "http://localhost/admin",
        "http://internal.example/",
        "http://metadata.example/latest/meta-data",
        "http://loopback.example/",
        "http://public.example:8080/",
        "http://user:pass@public.example/",
        "http://does-not-resolve.example/",
        "https://news.google.com/rss/articles/abc",
    ],
)
def test_rejects_unsafe_urls(resolver, url):
    with pytest.raises(ExtractionError):
        validate_public_url(url)


def test_accepts_public_url(resolver):
    validate_public_url("https://public.example/story")


class _Response:
    def __init__(self, status=200, headers=None, body=b""):
        self.status_code = status
        self.headers = headers or {}
        self.body = body

    @property
    def is_redirect(self):
        return self.status_code in (301, 302, 303, 307, 308) and "Location" in self.headers

    def iter_content(self, size):
        for i in range(0, len(self.body), size):
            yield self.body[i : i + size]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class _Session:
    def __init__(self, responses):
        self.responses = responses
        self.urls = []

    def get(self, url, **kwargs):
        self.urls.append(url)
        return self.responses[url]


def test_redirects_are_validated_at_every_hop(resolver):
    session = _Session({"https://public.example/a": _Response(302, {"Location": "http://internal.example/secret"})})
    with pytest.raises(ExtractionError) as info:
        fetch_html("https://public.example/a", session=session)
    assert info.value.code == "invalid_url"
    assert session.urls == ["https://public.example/a"]


def test_follows_safe_redirects(resolver):
    session = _Session(
        {
            "https://public.example/a": _Response(301, {"Location": "/b"}),
            "https://public.example/b": _Response(200, {"Content-Type": "text/html"}, b"<html>ok</html>"),
        }
    )
    final_url, body = fetch_html("https://public.example/a", session=session)
    assert final_url == "https://public.example/b"
    assert body == b"<html>ok</html>"


def test_paywalls_and_non_html_are_reported(resolver):
    session = _Session(
        {
            "https://public.example/paywall": _Response(403),
            "https://public.example/file.pdf": _Response(200, {"Content-Type": "application/pdf"}),
        }
    )
    with pytest.raises(ExtractionError) as info:
        fetch_html("https://public.example/paywall", session=session)
    assert info.value.code == "blocked"
    with pytest.raises(ExtractionError) as info:
        fetch_html("https://public.example/file.pdf", session=session)
    assert info.value.code == "not_html"


def test_oversized_pages_are_rejected(resolver, monkeypatch):
    monkeypatch.setattr(extract, "MAX_BYTES", 1000)
    session = _Session({"https://public.example/big": _Response(200, {"Content-Type": "text/html"}, b"x" * 5000)})
    with pytest.raises(ExtractionError) as info:
        fetch_html("https://public.example/big", session=session)
    assert info.value.code == "too_large"
