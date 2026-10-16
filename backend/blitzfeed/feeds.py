"""Headlines from publishers' RSS and Atom feeds: live, free, and no API key needed.

Each category merges a handful of feeds. Items come back in the same shape as NewsAPI
articles, so normalize_articles() treats both sources the same way.
"""

import calendar
import logging
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone

import feedparser
import requests

from .news import NewsAPIError

log = logging.getLogger(__name__)

MAX_FEED_BYTES = 3 * 1024 * 1024
ITEMS_PER_FEED = 25
# Older items only fill a category when its feeds are quiet.
MAX_AGE = 3 * 86_400
FEED_ACCEPT = "application/rss+xml, application/atom+xml, application/xml;q=0.9, */*;q=0.5"
USER_AGENT = "Mozilla/5.0 (compatible; BlitzFeed/2.0; +https://github.com/SairajBandre16/News-Summarizer)"


@dataclass(frozen=True)
class Feed:
    url: str
    source: str
    # False for publishers that block automated reading: their stories link out instead.
    summarizable: bool = True


def _f(url, source, summarizable=True):
    return Feed(url, source, summarizable)


# Checked on 2026-10-16: every feed returned fresh items, and article pages from the
# summarizable ones could be read.
FEEDS = {
    "us": {
        "general": (
            _f("https://feeds.npr.org/1001/rss.xml", "NPR"),
            _f("https://feeds.abcnews.com/abcnews/topstories", "ABC News"),
            _f("https://feeds.nbcnews.com/nbcnews/public/news", "NBC News"),
            _f("https://www.cbsnews.com/latest/rss/main", "CBS News"),
            _f("https://www.theguardian.com/us-news/rss", "The Guardian"),
            _f("https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml", "BBC News"),
        ),
        "business": (
            _f("https://www.cnbc.com/id/10001147/device/rss/rss.html", "CNBC"),
            _f("https://feeds.bbci.co.uk/news/business/rss.xml", "BBC News"),
            _f("https://www.theguardian.com/us/business/rss", "The Guardian"),
            _f("https://feeds.npr.org/1006/rss.xml", "NPR"),
        ),
        "technology": (
            _f("https://www.theverge.com/rss/index.xml", "The Verge"),
            _f("https://feeds.arstechnica.com/arstechnica/index", "Ars Technica"),
            _f("https://techcrunch.com/feed/", "TechCrunch"),
            _f("https://www.wired.com/feed/rss", "Wired"),
            _f("https://www.engadget.com/rss.xml", "Engadget"),
        ),
        "science": (
            _f("https://www.space.com/feeds/all", "Space.com"),
            _f("https://www.livescience.com/feeds/all", "Live Science"),
            _f("https://www.sciencedaily.com/rss/top/science.xml", "ScienceDaily"),
            _f("https://www.theguardian.com/science/rss", "The Guardian"),
            _f("https://feeds.npr.org/1007/rss.xml", "NPR"),
            _f("https://feeds.arstechnica.com/arstechnica/science", "Ars Technica"),
        ),
        "health": (
            _f("https://www.statnews.com/feed/", "STAT"),
            _f("https://feeds.bbci.co.uk/news/health/rss.xml", "BBC News"),
            _f("https://feeds.npr.org/1128/rss.xml", "NPR"),
            _f("https://www.sciencedaily.com/rss/top/health.xml", "ScienceDaily"),
        ),
        "sports": (
            _f("https://www.espn.com/espn/rss/news", "ESPN"),
            _f("https://www.cbssports.com/rss/headlines/", "CBS Sports"),
            _f("https://sports.yahoo.com/rss/", "Yahoo Sports"),
            _f("https://feeds.bbci.co.uk/sport/rss.xml", "BBC Sport"),
        ),
        "entertainment": (
            _f("https://variety.com/feed/", "Variety"),
            _f("https://deadline.com/feed/", "Deadline"),
            _f("https://www.hollywoodreporter.com/feed/", "The Hollywood Reporter"),
            _f("https://pitchfork.com/feed/feed-news/rss", "Pitchfork"),
            _f("https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml", "BBC News"),
        ),
    },
    "in": {
        "general": (
            _f("https://www.thehindu.com/news/national/feeder/default.rss", "The Hindu"),
            _f("https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml", "Hindustan Times"),
            _f("https://timesofindia.indiatimes.com/rssfeedstopstories.cms", "The Times of India"),
            _f("https://www.indiatoday.in/rss/1206578", "India Today"),
            _f("https://indianexpress.com/section/india/feed/", "The Indian Express"),
            _f("https://feeds.feedburner.com/ndtvnews-top-stories", "NDTV", summarizable=False),
        ),
        "business": (
            _f("https://www.livemint.com/rss/markets", "Mint"),
            _f("https://www.livemint.com/rss/companies", "Mint"),
            _f("https://economictimes.indiatimes.com/rssfeedstopstories.cms", "The Economic Times"),
            _f("https://www.thehindu.com/business/feeder/default.rss", "The Hindu"),
            _f("https://www.business-standard.com/rss/home_page_top_stories.rss", "Business Standard"),
            _f("https://indianexpress.com/section/business/feed/", "The Indian Express"),
        ),
        "technology": (
            _f("https://www.thehindu.com/sci-tech/technology/feeder/default.rss", "The Hindu"),
            _f("https://www.livemint.com/rss/technology", "Mint"),
            _f("https://indianexpress.com/section/technology/feed/", "The Indian Express"),
        ),
        "science": (
            _f("https://www.thehindu.com/sci-tech/science/feeder/default.rss", "The Hindu"),
            _f("https://www.thehindu.com/sci-tech/energy-and-environment/feeder/default.rss", "The Hindu"),
            _f("https://www.hindustantimes.com/feeds/rss/science/rssfeed.xml", "Hindustan Times"),
            _f("https://www.livemint.com/rss/science", "Mint"),
        ),
        "health": (
            _f("https://www.thehindu.com/sci-tech/health/feeder/default.rss", "The Hindu"),
            _f("https://indianexpress.com/section/lifestyle/health/feed/", "The Indian Express"),
            _f("https://www.hindustantimes.com/feeds/rss/lifestyle/health/rssfeed.xml", "Hindustan Times"),
        ),
        "sports": (
            _f("https://www.thehindu.com/sport/feeder/default.rss", "The Hindu"),
            _f("https://indianexpress.com/section/sports/feed/", "The Indian Express"),
            _f("https://www.hindustantimes.com/feeds/rss/sports/rssfeed.xml", "Hindustan Times"),
            _f("https://www.espncricinfo.com/rss/content/story/feeds/0.xml", "ESPNcricinfo", summarizable=False),
        ),
        "entertainment": (
            _f("https://www.thehindu.com/entertainment/feeder/default.rss", "The Hindu"),
            _f("https://www.hindustantimes.com/feeds/rss/entertainment/rssfeed.xml", "Hindustan Times"),
            _f("https://indianexpress.com/section/entertainment/feed/", "The Indian Express"),
            _f("https://www.bollywoodhungama.com/feed/", "Bollywood Hungama"),
        ),
    },
}

_IMG_RE = re.compile(r"<img[^>]+src=[\"']([^\"']+)[\"']", re.IGNORECASE)
# BBC feeds link 240px thumbnails; the same image is served at larger widths.
_BBC_IMAGE_RE = re.compile(r"(ichef\.bbci\.co\.uk/(?:ace/standard|news))/\d+/")


def _image(entry):
    best, best_width = None, -1
    for key in ("media_content", "media_thumbnail"):
        for media in entry.get(key) or []:
            url = media.get("url")
            kind = media.get("type") or media.get("medium") or "image"
            if not url or "image" not in kind:
                continue
            try:
                width = int(media.get("width") or 0)
            except ValueError:
                width = 0
            if width > best_width:
                best, best_width = url, width
    if not best:
        for link in entry.get("links") or []:
            if link.get("rel") == "enclosure" and (link.get("type") or "").startswith("image") and link.get("href"):
                best = link["href"]
                break
    if not best:
        for field in ("summary", "content"):
            value = entry.get(field)
            if isinstance(value, list):
                value = " ".join(part.get("value", "") for part in value)
            match = _IMG_RE.search(value or "")
            if match:
                best = match.group(1)
                break
    if best:
        best = _BBC_IMAGE_RE.sub(r"\1/800/", best.replace("&amp;", "&"))
    return best


def _published(entry, now):
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return None
    # Some feeds date items slightly in the future; clamp so "just now" stays honest.
    timestamp = min(calendar.timegm(parsed), now)
    return datetime.fromtimestamp(timestamp, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _description(entry):
    text = entry.get("summary") or ""
    # Plain text is enough here; normalize_articles strips tags and entities.
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > 320:
        text = text[:320].rsplit(" ", 1)[0] + "…"
    return text


def parse_feed(body, feed, now=None):
    """Raw NewsAPI-shaped articles from a feed document, newest first."""
    now = now or time.time()
    parsed = feedparser.parse(body)
    items = []
    for entry in parsed.entries:
        url, title = entry.get("link"), entry.get("title")
        if not url or not title:
            continue
        published = _published(entry, now)
        if published and now - calendar.timegm(time.strptime(published, "%Y-%m-%dT%H:%M:%SZ")) > MAX_AGE:
            continue
        items.append(
            {
                "source": {"id": None, "name": feed.source},
                "author": entry.get("author") or None,
                "title": title,
                "description": _description(entry),
                "url": url,
                "urlToImage": _image(entry),
                "publishedAt": published,
                "summarizable": feed.summarizable,
            }
        )
    items.sort(key=lambda item: item["publishedAt"] or "", reverse=True)
    return items[:ITEMS_PER_FEED]


def merge_feeds(feed_items):
    """Merge per-feed lists so the top of the page mixes outlets instead of listing one feed.

    Each later item from the same outlet is pushed back 30 minutes, so a busy feed can't
    crowd out the rest while fresh news still leads.
    """
    scored = []
    for items in feed_items:
        for rank, item in enumerate(items):
            stamp = item["publishedAt"]
            seconds = calendar.timegm(time.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ")) if stamp else 0
            scored.append((seconds - rank * 1800, item))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored]


class FeedClient:
    """Fetches feeds in parallel. Keeps each feed's last good copy for when a publisher is down."""

    def __init__(self, feeds=None, session=None, timeout=(4, 8), stale_ttl=86_400, workers=8):
        self.feeds = feeds or FEEDS
        self.session = session or requests.Session()
        self.timeout = timeout
        self.stale_ttl = stale_ttl
        self._pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="feeds")
        self._lock = threading.Lock()
        # url -> {"items", "fetched", "etag", "modified"}
        self._last_good = {}

    def top_headlines(self, edition, category="general"):
        feeds = self.feeds.get(edition.id, {}).get(category, ())
        if not feeds:
            raise NewsAPIError("no_feeds", f"No feeds are set up for {edition.id}/{category}.", 404)
        results = list(self._pool.map(self._load, feeds))
        if all(items is None for items in results):
            raise NewsAPIError("feeds_unavailable", "None of the news feeds could be reached.", 503)
        return merge_feeds([items for items in results if items])

    def _load(self, feed):
        with self._lock:
            previous = self._last_good.get(feed.url)
        headers = {"User-Agent": USER_AGENT, "Accept": FEED_ACCEPT}
        # Conditional requests: publishers answer 304 when nothing changed.
        if previous and previous.get("etag"):
            headers["If-None-Match"] = previous["etag"]
        if previous and previous.get("modified"):
            headers["If-Modified-Since"] = previous["modified"]
        try:
            with self.session.get(feed.url, headers=headers, timeout=self.timeout, stream=True) as response:
                if response.status_code == 304 and previous:
                    self._remember(feed, previous["items"], response, previous)
                    return previous["items"]
                response.raise_for_status()
                body = bytearray()
                for chunk in response.iter_content(64 * 1024):
                    body.extend(chunk)
                    if len(body) > MAX_FEED_BYTES:
                        raise ValueError("feed too large")
            items = parse_feed(bytes(body), feed)
            if not items and previous:
                raise ValueError("feed came back empty")
            self._remember(feed, items, response)
            return items
        except (requests.RequestException, ValueError) as exc:
            log.warning("Feed %s failed: %s", feed.url, exc.__class__.__name__)
            if previous and time.time() - previous["fetched"] < self.stale_ttl:
                return previous["items"]
            return None

    def _remember(self, feed, items, response, previous=None):
        previous = previous or {}
        with self._lock:
            self._last_good[feed.url] = {
                "items": items,
                "fetched": time.time(),
                "etag": response.headers.get("ETag") or previous.get("etag"),
                "modified": response.headers.get("Last-Modified") or previous.get("modified"),
            }
