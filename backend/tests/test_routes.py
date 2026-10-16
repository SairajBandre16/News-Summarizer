import pytest

from blitzfeed import routes
from blitzfeed.extract import ExtractionError
from blitzfeed.news import NewsAPIError, sign_url
from blitzfeed.summarizer import AIUnavailable

from .conftest import SAMPLE_TEXT, FakeNewsClient, raw_article


def test_health(client):
    body = client.get("/api/health").get_json()
    assert body["status"] == "ok"
    assert body["ai"]["enabled"] is False
    assert "technology" in body["categories"]


def test_news_paginates_from_one_upstream_call(app, client):
    first = client.get("/api/news?category=technology&limit=20").get_json()
    second = client.get("/api/news?category=technology&limit=20&offset=40").get_json()
    assert len(first["articles"]) == 20 and first["hasMore"] is True
    assert len(second["articles"]) == 5 and second["hasMore"] is False
    assert first["total"] == 45
    assert app.extensions["news_client"].calls == [("top", "us", "technology")]
    assert first["articles"][0]["sig"]


def test_headlines_rank_link_only_stories_last(app, client):
    app.extensions["news_client"].articles = [
        raw_article(1, url="https://news.google.com/rss/articles/abc", urlToImage=None),
        raw_article(2, urlToImage=None),
        raw_article(3),
        raw_article(4),
    ]
    urls = [a["url"] for a in client.get("/api/news").get_json()["articles"]]
    assert urls == [
        "https://example.com/story-3",
        "https://example.com/story-4",
        "https://news.google.com/rss/articles/abc",
        "https://example.com/story-2",
    ]


@pytest.mark.parametrize(
    "query, code",
    [
        ("edition=mars", "invalid_edition"),
        ("category=politics", "invalid_category"),
        ("offset=abc", "invalid_parameter"),
    ],
)
def test_news_validates_input(client, query, code):
    response = client.get(f"/api/news?{query}")
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == code


def test_news_serves_stale_copy_when_upstream_fails(app, client):
    client.get("/api/news")
    with app.app_context():
        routes.cache.delete("feed:newsapi:us:general")
    app.extensions["news_client"].error = NewsAPIError("rateLimited", "too many", 503)
    body = client.get("/api/news").get_json()
    assert body["stale"] is True and body["articles"]


def test_news_error_without_cache_hides_upstream_message(app, client):
    app.extensions["news_client"] = FakeNewsClient(error=NewsAPIError("apiKeyInvalid", "key abc123 is bad", 502))
    response = client.get("/api/news")
    assert response.status_code == 502
    assert "abc123" not in response.get_data(as_text=True)


def test_search_requires_query_and_validates_sort(client):
    assert client.get("/api/search").status_code == 400
    assert client.get("/api/search?q=ai&sort=random").status_code == 400
    body = client.get("/api/search?q=%20electric%20%20cars%20").get_json()
    assert body["query"] == "electric cars"


def _fake_article(url):
    return {
        "url": url,
        "title": "Council approves $2.4 billion transit plan",
        "author": "Reporter",
        "publishedAt": "2026-10-16",
        "image": None,
        "siteName": "Springfield Daily",
        "text": SAMPLE_TEXT,
        "wordCount": len(SAMPLE_TEXT.split()),
    }


def test_summarize_rejects_unsigned_urls(client):
    response = client.post("/api/summarize", json={"url": "https://example.com/a", "sig": "nope"})
    assert response.status_code == 403


def test_summarize_extractive_and_cached(app, client, monkeypatch):
    calls = []
    monkeypatch.setattr(routes, "extract_article", lambda url: calls.append(url) or _fake_article(url))
    url = "https://example.com/story"
    payload = {"url": url, "sig": sign_url("test-secret", url)}

    first = client.post("/api/summarize", json=payload).get_json()
    second = client.post("/api/summarize", json=payload).get_json()
    assert first["mode"] == "extractive"
    assert first["summary"]["tldr"]
    assert first["readingMinutes"] >= 1
    assert second == first and calls == [url]


def test_summarize_reports_and_caches_extraction_failures(client, monkeypatch):
    calls = []

    def fail(url):
        calls.append(url)
        raise ExtractionError("blocked", "The publisher blocks automated reading.")

    monkeypatch.setattr(routes, "extract_article", fail)
    url = "https://example.com/paywalled"
    payload = {"url": url, "sig": sign_url("test-secret", url)}
    for _ in range(2):
        response = client.post("/api/summarize", json=payload)
        assert response.status_code == 422
        assert response.get_json()["error"]["code"] == "blocked"
    assert len(calls) == 1


class _FakeAI:
    model = "claude-opus-5-5"

    def __init__(self, fail=False):
        self.fail = fail

    def summarize(self, title, source, text):
        if self.fail:
            raise AIUnavailable("down")
        return {
            "tldr": "The council approved a transit plan.",
            "keyPoints": ["Three new lines.", "Funded by sales tax."],
            "whyItMatters": "Commutes get shorter.",
            "sentiment": "positive",
            "topics": ["Transit"],
        }, False

    def briefing(self, articles):
        if self.fail:
            raise AIUnavailable("down")
        return {"intro": "Busy day.", "items": [{"article": articles[0], "headline": "H", "summary": "S"}]}


def test_summarize_uses_ai_when_available(app, client, monkeypatch):
    app.extensions["ai"] = _FakeAI()
    monkeypatch.setattr(routes, "extract_article", _fake_article)
    url = "https://example.com/ai"
    body = client.post("/api/summarize", json={"url": url, "sig": sign_url("test-secret", url)}).get_json()
    assert body["mode"] == "ai" and body["summary"]["sentiment"] == "positive"
    assert body["model"] == "claude-opus-5-5"


def test_summarize_falls_back_when_ai_fails(app, client, monkeypatch):
    app.extensions["ai"] = _FakeAI(fail=True)
    monkeypatch.setattr(routes, "extract_article", _fake_article)
    url = "https://example.com/ai-down"
    body = client.post("/api/summarize", json={"url": url, "sig": sign_url("test-secret", url)}).get_json()
    assert body["mode"] == "extractive" and body["notice"]


def test_briefing_with_and_without_ai(app, client):
    basic = client.get("/api/briefing").get_json()
    assert basic["mode"] == "headlines" and len(basic["items"]) == 5

    app.extensions["ai"] = _FakeAI()
    ai = client.get("/api/briefing").get_json()
    assert ai["mode"] == "ai" and ai["intro"] == "Busy day."


def test_unknown_route_returns_json(client):
    response = client.get("/api/nope")
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "not_found"
