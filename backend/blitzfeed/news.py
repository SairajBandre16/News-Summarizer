"""NewsAPI client, editions, and article normalization (shared with the RSS feeds)."""

import hashlib
import hmac
import html
import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

import requests

CATEGORIES = ("general", "business", "technology", "science", "health", "sports", "entertainment")
SORT_OPTIONS = ("publishedAt", "relevancy", "popularity")

# Hosts whose links are redirects or consent walls, so they can't be summarized.
UNSUMMARIZABLE_HOSTS = {"news.google.com", "consent.google.com", "www.youtube.com", "youtube.com"}


@dataclass(frozen=True)
class Edition:
    id: str
    label: str
    country: str = ""
    # Editions without working country headlines search a set of local domains instead.
    domains: tuple = ()
    category_queries: dict = field(default_factory=dict)


# NewsAPI only returns top headlines by country for the US on current plans
# (country=in returns zero results), so the India edition is built from Indian outlets.
EDITIONS = {
    "us": Edition(id="us", label="United States", country="us"),
    "in": Edition(
        id="in",
        label="India",
        domains=(
            "livemint.com",
            "business-standard.com",
            "moneycontrol.com",
            "indiatoday.in",
            "hindustantimes.com",
            "theprint.in",
            "indianexpress.com",
            "deccanherald.com",
        ),
        category_queries={
            "business": "business OR economy OR markets OR stocks OR RBI OR earnings",
            "technology": "technology OR tech OR AI OR startup OR smartphone OR software",
            "science": "science OR ISRO OR research OR space OR climate",
            "health": "health OR hospital OR disease OR medical OR vaccine",
            "sports": "cricket OR football OR sports OR IPL OR hockey OR Olympics",
            "entertainment": "Bollywood OR film OR movie OR music OR celebrity OR OTT",
        },
    ),
}


class NewsAPIError(Exception):
    """A failure talking to NewsAPI, with a status code suitable for our own response."""

    def __init__(self, code, message, status=502):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


class NewsClient:
    def __init__(self, api_key, base_url="https://newsapi.org/v2", session=None, timeout=(4, 10)):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.timeout = timeout

    def top_headlines(self, edition, category="general"):
        if edition.country:
            params = {"country": edition.country, "pageSize": 100}
            if category != "general":
                params["category"] = category
            return self._get("top-headlines", params)
        params = {
            "domains": ",".join(edition.domains),
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 100,
        }
        query = edition.category_queries.get(category)
        if query:
            params["q"] = query
            params["searchIn"] = "title,description"
        return self._get("everything", params)

    def search(self, query, edition, sort="publishedAt"):
        params = {"q": query, "language": "en", "sortBy": sort, "pageSize": 100}
        if edition.domains:
            params["domains"] = ",".join(edition.domains)
        return self._get("everything", params)

    def _get(self, path, params):
        if not self.api_key:
            raise NewsAPIError("not_configured", "NEWS_API_KEY is not set on the server.", 503)
        try:
            response = self.session.get(
                f"{self.base_url}/{path}",
                params=params,
                headers={"X-Api-Key": self.api_key, "User-Agent": "BlitzFeed/2.0"},
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise NewsAPIError("upstream_unreachable", "Couldn't reach the news provider.") from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise NewsAPIError("upstream_invalid", "The news provider sent an unreadable response.") from exc

        if data.get("status") != "ok":
            code = data.get("code", "upstream_error")
            status = 503 if code in ("rateLimited", "maximumResultsReached") else 502
            raise NewsAPIError(code, data.get("message") or "The news provider returned an error.", status)
        return data.get("articles") or []


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")
_TRUNCATION_RE = re.compile(r"\s*(\[\+\d+ chars\]|\[…\]|\[\.\.\.\])\s*$")


def _clean_text(value):
    if not value or not isinstance(value, str):
        return ""
    text = html.unescape(_TAG_RE.sub(" ", value))
    text = _TRUNCATION_RE.sub("", text)
    return _SPACE_RE.sub(" ", text).strip()


def _split_publisher(title, source_name):
    """NewsAPI titles often end in ' - Publisher'. Strip it, and use it as the source for aggregators."""
    if " - " not in title:
        return title, source_name
    head, tail = title.rsplit(" - ", 1)
    tail = tail.strip()
    if not head.strip() or len(tail) > 60:
        return title, source_name
    if source_name in ("", "Google News"):
        return head.strip(), tail
    if _same_publisher(tail, source_name):
        return head.strip(), source_name
    return title, source_name


def _same_publisher(a, b):
    """'BBC' and 'BBC News' name the same outlet: one is a whole-word part of the other."""
    a, b = a.lower().strip(), b.lower().strip()
    if a == b:
        return True
    shorter, longer = sorted((a, b), key=len)
    return len(shorter) >= 3 and re.search(rf"\b{re.escape(shorter)}\b", longer) is not None


def _http_url(value):
    if not isinstance(value, str):
        return None
    parsed = urlparse(value.strip())
    if parsed.scheme in ("http", "https") and parsed.netloc:
        return value.strip()
    return None


def article_id(url):
    return hashlib.sha1(url.encode()).hexdigest()[:16]


def sign_url(secret, url):
    return hmac.new(secret.encode(), url.encode(), hashlib.sha256).hexdigest()[:32]


def verify_url(secret, url, signature):
    if not isinstance(signature, str) or not isinstance(url, str):
        return False
    return hmac.compare_digest(sign_url(secret, url), signature)


def normalize_articles(raw_articles, secret):
    """Turn NewsAPI articles into the shape the frontend uses, dropping junk and duplicates."""
    seen_urls, seen_titles, articles = set(), set(), []
    for raw in raw_articles:
        url = _http_url(raw.get("url"))
        title = _clean_text(raw.get("title"))
        if not url or not title or title == "[Removed]":
            continue

        source_name = _clean_text((raw.get("source") or {}).get("name"))
        title, source_name = _split_publisher(title, source_name)

        title_key = re.sub(r"\W+", "", title.lower())
        if url in seen_urls or title_key in seen_titles:
            continue
        seen_urls.add(url)
        seen_titles.add(title_key)

        description = _clean_text(raw.get("description"))
        if description.lower() == title.lower():
            description = ""

        host = urlparse(url).hostname or ""
        articles.append(
            {
                "id": article_id(url),
                "title": title,
                "description": description,
                "url": url,
                "image": _http_url(raw.get("urlToImage")),
                "source": source_name or host.removeprefix("www."),
                "author": _clean_text(raw.get("author")) or None,
                "publishedAt": raw.get("publishedAt"),
                "summarizable": host not in UNSUMMARIZABLE_HOSTS and raw.get("summarizable", True),
                "sig": sign_url(secret, url),
            }
        )
    return articles
