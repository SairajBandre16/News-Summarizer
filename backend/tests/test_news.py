from blitzfeed.news import EDITIONS, NewsClient, normalize_articles, sign_url, verify_url

from .conftest import raw_article


def test_normalize_drops_removed_and_duplicate_articles():
    raw = [
        raw_article(1),
        raw_article(1),  # same url
        raw_article(2, title="Headline1 arrives"),  # same title, different url
        raw_article(3, title="[Removed]"),
        raw_article(4, url="javascript:alert(1)"),
        raw_article(5, title=None),
    ]
    articles = normalize_articles(raw, "secret")
    assert [a["url"] for a in articles] == ["https://example.com/story-1"]


def test_normalize_strips_publisher_suffix_and_html():
    raw = [
        raw_article(1, title="Markets rally - Fox Business", source={"name": "Fox Business"}),
        raw_article(2, title="iPhone news - 9to5Mac", source={"name": "Google News"},
                    url="https://news.google.com/rss/articles/abc", description="<p>Hi &amp; bye</p> [+120 chars]"),
    ]
    first, second = normalize_articles(raw, "secret")
    assert first["title"] == "Markets rally"
    assert first["source"] == "Fox Business"
    assert second["title"] == "iPhone news"
    assert second["source"] == "9to5Mac"
    assert second["description"] == "Hi & bye"
    assert second["summarizable"] is False
    assert first["summarizable"] is True


def test_normalize_strips_short_form_of_publisher_name():
    raw = [
        raw_article(1, title="Storm hits coast - BBC", source={"name": "BBC News"}),
        raw_article(2, title="Rates hold steady - Reuters.com", source={"name": "Reuters"}),
        raw_article(3, title="Q3 results - AP", source={"name": "AP News"}),
    ]
    first, second, third = normalize_articles(raw, "secret")
    assert (first["title"], first["source"]) == ("Storm hits coast", "BBC News")
    assert second["title"] == "Rates hold steady"
    assert third["title"] == "Q3 results - AP"  # too short to match safely


def test_normalize_keeps_hyphenated_titles_from_other_sources():
    [article] = normalize_articles([raw_article(1, title="Biden - Trump debate recap", source={"name": "CNN"})], "s")
    assert article["title"] == "Biden - Trump debate recap"


def test_signatures_verify_only_for_the_signed_url():
    signature = sign_url("secret", "https://example.com/a")
    assert verify_url("secret", "https://example.com/a", signature)
    assert not verify_url("secret", "https://example.com/b", signature)
    assert not verify_url("other", "https://example.com/a", signature)
    assert not verify_url("secret", "https://example.com/a", None)


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


class _Session:
    def __init__(self, payload):
        self.payload = payload
        self.requests = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.requests.append((url, params, headers))
        return _Response(self.payload)


def test_client_sends_key_in_header_and_encodes_query_as_params():
    session = _Session({"status": "ok", "articles": []})
    NewsClient("key", session=session).search("ai & robots", EDITIONS["us"])
    url, params, headers = session.requests[0]
    assert url.endswith("/everything")
    assert params["q"] == "ai & robots"
    assert "apiKey" not in params and headers["X-Api-Key"] == "key"


def test_india_edition_uses_domains_and_category_queries():
    session = _Session({"status": "ok", "articles": []})
    NewsClient("key", session=session).top_headlines(EDITIONS["in"], "sports")
    url, params, _ = session.requests[0]
    assert url.endswith("/everything")
    assert "livemint.com" in params["domains"]
    assert "cricket" in params["q"]


def test_client_raises_on_api_error():
    session = _Session({"status": "error", "code": "rateLimited", "message": "slow down"})
    try:
        NewsClient("key", session=session).top_headlines(EDITIONS["us"])
    except Exception as exc:
        assert exc.code == "rateLimited" and exc.status == 503
    else:
        raise AssertionError("expected NewsAPIError")
