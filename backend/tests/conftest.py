import pytest

from blitzfeed import create_app
from blitzfeed.extensions import cache

SAMPLE_TEXT = """
The city council approved a $2.4 billion transit plan on Tuesday, clearing the way for three new light rail lines across Springfield.
Mayor Dana Ortiz said the Springfield Transit Plan would cut average commute times by 18 minutes for more than 200,000 residents.
Construction on the first line, connecting the airport to downtown Springfield, is expected to begin next spring.
The plan will be funded by a half-cent sales tax increase that voters approved last November, along with federal grants.
Critics on the council argued the Springfield Transit Plan underestimates construction costs and could face long delays.
Councilmember Lee Park, who voted against the measure, said similar projects in other cities ran 40 percent over budget.
Supporters countered that the light rail lines would reduce traffic congestion and air pollution across the region.
The transit authority will hold public meetings next month to gather feedback on station locations.
Mayor Dana Ortiz called the vote a historic day for the city and thanked residents for their patience.
Officials expect the first light rail line to open to passengers in 2030 if construction stays on schedule.
"""


def raw_article(n, **overrides):
    article = {
        "source": {"id": None, "name": f"Source {n}"},
        "author": "Reporter",
        "title": f"Headline{n} arrives",
        "description": f"Description for story {n}.",
        "url": f"https://example.com/story-{n}",
        "urlToImage": f"https://example.com/img-{n}.jpg",
        "publishedAt": "2026-10-16T08:00:00Z",
        "content": "",
    }
    article.update(overrides)
    return article


class FakeNewsClient:
    def __init__(self, articles=None, error=None):
        self.articles = articles if articles is not None else [raw_article(n) for n in range(1, 46)]
        self.error = error
        self.calls = []

    def top_headlines(self, edition, category="general"):
        self.calls.append(("top", edition.id, category))
        if self.error:
            raise self.error
        return self.articles

    def search(self, query, edition, sort="publishedAt"):
        self.calls.append(("search", query, edition.id, sort))
        if self.error:
            raise self.error
        return self.articles


@pytest.fixture
def app():
    app = create_app(
        {
            "TESTING": True,
            "NEWS_API_KEY": "test-key",
            "SECRET_KEY": "test-secret",
            "ANTHROPIC_API_KEY": "",
            "GROQ_API_KEY": "",
            # Route tests drive headlines through FakeNewsClient; test_feeds covers RSS.
            "NEWS_SOURCE": "newsapi",
            "RATELIMIT_ENABLED": False,
            "CACHE_TYPE": "SimpleCache",
        }
    )
    app.extensions["ai"] = None
    app.extensions["news_client"] = FakeNewsClient()
    app.extensions["feed_client"] = FakeNewsClient()
    with app.app_context():
        cache.clear()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()
