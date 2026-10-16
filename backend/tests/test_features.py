"""RSS feeds, story grouping, local search, Ask this story, and Compare coverage."""

import json
import time

import pytest
import requests
from requests.structures import CaseInsensitiveDict

from blitzfeed import routes
from blitzfeed.coverage import group_stories
from blitzfeed.extract import ExtractionError
from blitzfeed.feeds import Feed, FeedClient, merge_feeds, parse_feed
from blitzfeed.news import EDITIONS, NewsAPIError, normalize_articles, sign_url
from blitzfeed.summarizer import AIUnavailable, GroqSummarizer, extractive_answer

from .conftest import SAMPLE_TEXT, FakeNewsClient, raw_article
from .test_groq import FakeResponse, FakeSession, make_budget

NOW = time.time()


def _rfc822(seconds_ago):
    return time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(NOW - seconds_ago))


RSS = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
  <channel>
    <title>Example News</title>
    <item>
      <title>Council approves transit plan</title>
      <link>https://example.com/transit</link>
      <description><![CDATA[<p>The <b>council</b> voted 7-2.</p><img src="https://example.com/inline.jpg">]]></description>
      <pubDate>{_rfc822(3600)}</pubDate>
      <media:content url="https://example.com/small.jpg" medium="image" width="140" />
      <media:content url="https://example.com/large.jpg" medium="image" width="1200" />
    </item>
    <item>
      <title>BBC style thumbnail</title>
      <link>https://example.com/bbc</link>
      <description>Short text.</description>
      <pubDate>{_rfc822(-7200)}</pubDate>
      <media:thumbnail url="https://ichef.bbci.co.uk/ace/standard/240/cpsprodpb/abc.jpg" width="240" />
    </item>
    <item>
      <title>Inline image only</title>
      <link>https://example.com/inline</link>
      <description><![CDATA[<img src="https://example.com/inline.png" /> Body]]></description>
      <pubDate>{_rfc822(7200)}</pubDate>
    </item>
    <item>
      <title>Old news</title>
      <link>https://example.com/old</link>
      <pubDate>{_rfc822(10 * 86400)}</pubDate>
    </item>
    <item><title>No link</title></item>
  </channel>
</rss>""".encode()

ATOM = f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Atom Example</title>
  <entry>
    <title>Atom story</title>
    <link href="https://example.org/atom-story" />
    <updated>{time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(NOW - 600))}</updated>
    <summary>An Atom summary.</summary>
  </entry>
</feed>""".encode()


# Feeds


def test_parse_rss_picks_images_dates_and_text():
    items = parse_feed(RSS, Feed("https://example.com/rss", "Example"), now=NOW)
    by_url = {item["url"]: item for item in items}

    assert set(by_url) == {"https://example.com/transit", "https://example.com/bbc", "https://example.com/inline"}
    transit = by_url["https://example.com/transit"]
    assert transit["urlToImage"] == "https://example.com/large.jpg"
    assert transit["description"] == "The council voted 7-2."
    assert transit["source"]["name"] == "Example" and transit["summarizable"] is True
    # BBC thumbnails are upgraded, and future dates are clamped to now.
    bbc = by_url["https://example.com/bbc"]
    assert "/800/" in bbc["urlToImage"]
    assert bbc["publishedAt"] == time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(NOW))
    assert by_url["https://example.com/inline"]["urlToImage"] == "https://example.com/inline.png"
    # Newest first.
    assert items[0]["url"] == "https://example.com/bbc"


def test_parse_atom_and_link_only_feeds():
    [item] = parse_feed(ATOM, Feed("https://example.org/atom", "Atom", summarizable=False), now=NOW)
    assert item["title"] == "Atom story" and item["url"] == "https://example.org/atom-story"
    assert item["summarizable"] is False
    [article] = normalize_articles([item], "s")
    assert article["summarizable"] is False


def test_merge_feeds_mixes_outlets():
    def items(source, count):
        return [
            {"source": {"name": source}, "publishedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(NOW - i * 60))}
            for i in range(count)
        ]

    merged = merge_feeds([items("Busy", 5), items("Quiet", 2)])
    top = [item["source"]["name"] for item in merged[:4]]
    assert top.count("Quiet") == 2


class FeedResponse:
    def __init__(self, status=200, body=b"", headers=None):
        self.status_code = status
        self.body = body
        self.headers = CaseInsensitiveDict(headers or {})

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))

    def iter_content(self, size):
        yield self.body


class FeedSession:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []

    def get(self, url, headers=None, timeout=None, stream=False):
        self.requests.append(headers)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _client(session, feeds=None):
    feeds = feeds or {"us": {"general": (Feed("https://example.com/rss", "Example"),)}}
    return FeedClient(feeds=feeds, session=session, workers=2)


def test_feed_client_uses_conditional_requests_and_last_good_copy():
    session = FeedSession(
        FeedResponse(200, RSS, {"ETag": '"v1"'}),
        FeedResponse(304),
        requests.ConnectionError("down"),
    )
    client = _client(session)
    first = client.top_headlines(EDITIONS["us"])
    assert len(first) == 3
    assert client.top_headlines(EDITIONS["us"]) == first
    assert session.requests[1]["If-None-Match"] == '"v1"'
    # A failing publisher serves its last good copy.
    assert client.top_headlines(EDITIONS["us"]) == first


def test_feed_client_raises_when_every_feed_fails():
    client = _client(FeedSession(requests.ConnectionError("down")))
    with pytest.raises(NewsAPIError) as exc:
        client.top_headlines(EDITIONS["us"])
    assert exc.value.status == 503


# Story grouping


def _article(n, title, source, image=True, description=""):
    raw = raw_article(n, title=title, source={"name": source}, description=description)
    if not image:
        raw["urlToImage"] = None
    return normalize_articles([raw], "s")[0]


def test_group_stories_merges_one_event_across_outlets():
    articles = [
        _article(1, "Oregon school shooting suspect identified by police", "ABC News", image=False),
        _article(2, "Police identify suspect in Oregon school shooting", "CBS News"),
        _article(3, "Oregon school shooting: what we know about the suspect", "ABC News"),
        _article(4, "Stocks rally as inflation cools", "CNBC"),
        _article(5, "Oregon shooting suspect named as police search for motive", "NBC News"),
    ]
    grouped = group_stories(articles)

    assert [a["title"] for a in grouped][1:] == [
        "Oregon school shooting: what we know about the suspect",
        "Stocks rally as inflation cools",
    ]
    lead = grouped[0]
    # The version with a photo leads; the other outlets ride along.
    assert lead["source"] == "CBS News"
    assert {r["source"] for r in lead["related"]} == {"ABC News", "NBC News"}
    assert set(lead["related"][0]) == {"id", "title", "source", "url", "sig", "publishedAt", "summarizable"}
    assert "related" not in grouped[2]


def test_group_stories_keeps_unrelated_stories_apart():
    articles = [
        _article(1, "Trump rallies supporters in Georgia", "NPR"),
        _article(2, "Trump comments on Ukraine strikes", "NBC News"),
    ]
    assert all("related" not in a for a in group_stories(articles))


def test_news_from_rss_groups_related_stories(app, client):
    app.config["NEWS_SOURCE"] = "rss"
    app.extensions["feed_client"] = FakeNewsClient(
        [
            raw_article(1, title="Council approves Springfield transit plan", source={"name": "NPR"}),
            raw_article(2, title="Springfield council approves transit plan", source={"name": "BBC News"}),
            raw_article(3, title="Lakers win in overtime", source={"name": "ESPN"}),
        ]
    )
    body = client.get("/api/news").get_json()
    assert body["total"] == 2
    assert body["articles"][0]["related"][0]["source"] == "BBC News"
    assert client.get("/api/health").get_json()["newsSource"] == "rss"


# Local search


def test_search_without_newsapi_key_searches_the_feeds(app, client):
    app.config["NEWS_API_KEY"] = ""
    app.extensions["news_client"] = FakeNewsClient(
        [
            raw_article(1, title="Transit plan approved", description="Springfield votes for rail."),
            raw_article(2, title="Rail strike ends", description="Workers return."),
            raw_article(3, title="Council budget", description="The transit plan is funded by a sales tax."),
        ]
    )
    body = client.get("/api/search?q=transit%20plan&sort=relevancy").get_json()
    assert body["searchSource"] == "feeds"
    assert [a["title"] for a in body["articles"]] == ["Transit plan approved", "Council budget"]
    # No story has every word, so any word counts.
    loose = client.get("/api/search?q=rail%20weather").get_json()
    assert {a["title"] for a in loose["articles"]} == {"Transit plan approved", "Rail strike ends"}


# Ask this story


def _fake_article(url):
    return {
        "url": url,
        "title": "Council approves $2.4 billion transit plan",
        "author": None,
        "publishedAt": None,
        "image": None,
        "siteName": "Springfield Daily",
        "text": SAMPLE_TEXT,
        "wordCount": len(SAMPLE_TEXT.split()),
    }


class FakeAI:
    model = "test-model"
    provider = "groq"

    def __init__(self, fail=False):
        self.fail = fail
        self.calls = []

    def ask(self, title, source, text, question):
        self.calls.append(("ask", question))
        if self.fail:
            raise AIUnavailable("down")
        return {"answerable": True, "answer": "In 2030.", "quote": "open to passengers in 2030"}

    def compare(self, items):
        self.calls.append(("compare", [i["source"] for i in items]))
        if self.fail:
            raise AIUnavailable("down")
        return {
            "sameEvent": True,
            "event": "A transit plan passed.",
            "commonGround": ["The vote passed."],
            "outlets": [{"index": 1, "angle": "Costs.", "unique": []}, {"index": 0, "angle": "Commutes.", "unique": ["18 minutes"]}],
            "differences": [],
        }


def _signed(url):
    return {"url": url, "sig": sign_url("test-secret", url)}


def test_ask_extractive_answer_and_cache(app, client, monkeypatch):
    calls = []
    monkeypatch.setattr(routes, "extract_article", lambda url: calls.append(url) or _fake_article(url))
    payload = {**_signed("https://example.com/a"), "question": "When will the first line open?"}

    body = client.post("/api/ask", json=payload).get_json()
    assert body["mode"] == "extractive" and body["answerable"] is True
    assert any("2030" in p for p in body["passages"])
    client.post("/api/ask", json={**payload, "question": "  when will the FIRST line open? "})
    client.post("/api/ask", json={**payload, "question": "Who voted against it?"})
    assert len(calls) == 1  # the article text is fetched once and reused


def test_ask_uses_ai_and_falls_back(app, client, monkeypatch):
    monkeypatch.setattr(routes, "extract_article", _fake_article)
    app.extensions["ai"] = FakeAI()
    body = client.post("/api/ask", json={**_signed("https://example.com/b"), "question": "When?"}).get_json()
    assert body["mode"] == "ai" and body["answer"] == "In 2030." and body["quote"]

    app.extensions["ai"] = FakeAI(fail=True)
    body = client.post("/api/ask", json={**_signed("https://example.com/c"), "question": "When does it open?"}).get_json()
    assert body["mode"] == "extractive" and body["notice"]


@pytest.mark.parametrize(
    "payload, status, code",
    [
        ({"question": "Why?"}, 400, "invalid_url"),
        ({"url": "https://example.com/a", "sig": "forged", "question": "Why?"}, 403, "invalid_signature"),
        ({**_signed("https://example.com/a"), "question": " ? "}, 400, "missing_question"),
        ({**_signed("https://example.com/a"), "question": "x" * 301}, 400, "question_too_long"),
    ],
)
def test_ask_validates_input(client, payload, status, code):
    response = client.post("/api/ask", json=payload)
    assert response.status_code == status and response.get_json()["error"]["code"] == code


# Compare coverage


def test_compare_extractive_and_ai(app, client, monkeypatch):
    monkeypatch.setattr(routes, "extract_article", _fake_article)
    stories = [_signed("https://example.com/one"), _signed("https://example.com/two")]

    body = client.post("/api/compare", json={"stories": stories}).get_json()
    assert body["mode"] == "extractive" and len(body["outlets"]) == 2
    assert body["outlets"][0]["angle"]

    app.extensions["ai"] = FakeAI()
    stories = [_signed("https://example.com/three"), _signed("https://example.com/four")]
    body = client.post("/api/compare", json={"stories": stories}).get_json()
    assert body["mode"] == "ai" and body["sameEvent"] is True
    assert [o["url"] for o in body["outlets"]] == ["https://example.com/four", "https://example.com/three"]


def test_compare_needs_two_readable_stories(client, monkeypatch):
    def extract(url):
        if url.endswith("blocked"):
            raise ExtractionError("blocked", "Paywall.")
        return _fake_article(url)

    monkeypatch.setattr(routes, "extract_article", extract)
    stories = [_signed("https://example.com/ok"), _signed("https://example.com/blocked")]
    response = client.post("/api/compare", json={"stories": stories})
    assert response.status_code == 422 and response.get_json()["error"]["code"] == "not_enough_text"


@pytest.mark.parametrize(
    "stories",
    [None, [], [_signed("https://example.com/a")], [_signed("https://example.com/a")] * 2, ["https://example.com/a"] * 2],
)
def test_compare_validates_input(client, stories):
    assert client.post("/api/compare", json={"stories": stories}).status_code == 400


# AI writer: answers and comparisons


def _groq_reply(content):
    payload = {
        "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(content)}}],
        "usage": {"prompt_tokens": 500, "completion_tokens": 100, "total_tokens": 600},
    }
    return FakeResponse(200, payload)


def test_groq_ask_drops_quotes_that_are_not_in_the_article():
    reply = {"answerable": True, "answer": "In 2030.", "quote": "the line opens in 2031"}
    session = FakeSession(_groq_reply(reply), _groq_reply({**reply, "quote": "open to passengers in 2030"}))
    writer = GroqSummarizer("k", "openai/gpt-oss-120b", make_budget()[0], session=session)

    assert writer.ask("T", "S", SAMPLE_TEXT, "When?")["quote"] is None
    assert writer.ask("T", "S", SAMPLE_TEXT, "When?")["quote"] == "open to passengers in 2030"
    body = session.calls[0]["json"]
    assert body["max_completion_tokens"] == 500
    assert "<question>\nWhen?\n</question>" in body["messages"][1]["content"]


def test_groq_compare_maps_outlets_and_clips_each_article():
    reply = {
        "sameEvent": True,
        "event": "A plan passed.",
        "commonGround": ["Vote passed.", " "],
        "outlets": [{"index": 2, "angle": "Costs.", "unique": []}, {"index": 9, "angle": "Bogus.", "unique": []}],
        "differences": [],
    }
    session = FakeSession(_groq_reply(reply))
    writer = GroqSummarizer("k", "openai/gpt-oss-120b", make_budget()[0], session=session, max_input_chars=2000)
    items = [{"source": f"Outlet {n}", "title": "T", "text": "Word " * 2000} for n in range(3)]

    result = writer.compare(items)
    assert result["outlets"] == [{"index": 1, "angle": "Costs.", "unique": []}]
    assert result["commonGround"] == ["Vote passed."]
    content = session.calls[0]["json"]["messages"][1]["content"]
    assert content.count("<article number=") == 3 and len(content) < 3 * 1000 + 600


def test_extractive_answer_finds_matching_sentences():
    passages = extractive_answer(SAMPLE_TEXT, "How is the plan funded?")
    assert any("sales tax" in p for p in passages)
    assert extractive_answer(SAMPLE_TEXT, "the of and") == []
