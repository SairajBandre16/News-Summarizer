"""HTTP endpoints, all under /api."""

import hashlib
import logging
import threading
import zlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib.parse import urlparse

from flask import Blueprint, current_app, jsonify, request

from . import __version__
from .coverage import group_stories
from .errors import APIError
from .extensions import cache, limiter
from .extract import ExtractionError, extract_article
from .news import CATEGORIES, EDITIONS, SORT_OPTIONS, NewsAPIError, article_id, normalize_articles, verify_url
from .summarizer import AIUnavailable, content_terms, extractive_answer, extractive_summary, reading_minutes

log = logging.getLogger(__name__)
bp = Blueprint("api", __name__, url_prefix="/api")

FAILED_SUMMARY_TTL = 900
DEGRADED_TTL = 300
# A fallback answer is cheap to redo, so asking again soon gets another try at the AI.
DEGRADED_ANSWER_TTL = 60
ARTICLE_TTL = 6 * 3600
SEARCH_TTL = 300

# Striped locks so concurrent requests for the same uncached item do the work once
# (protects the news quota and avoids duplicate AI calls). RLock allows nesting.
_LOCKS = [threading.RLock() for _ in range(64)]
# Article fetches get their own stripes. They are taken while an outer lock is held
# (a summary, answer or comparison), never the other way round, so they can't deadlock.
_ARTICLE_LOCKS = [threading.RLock() for _ in range(64)]
_ARTICLE_POOL = ThreadPoolExecutor(max_workers=8, thread_name_prefix="articles")


def _lock_for(key, locks=_LOCKS):
    return locks[zlib.crc32(key.encode()) % len(locks)]


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _cached_feed(key, loader, rich_first=False, group=False):
    """Serve from cache; refetch once on a miss; fall back to the last good copy if the source fails."""
    config = current_app.config
    hit = cache.get(key)
    if hit is not None:
        return hit, False
    with _lock_for(key):
        hit = cache.get(key)
        if hit is not None:
            return hit, False
        try:
            articles = normalize_articles(loader(), config["SECRET_KEY"])
            if group:
                # One card per event; other outlets' versions ride along in `related`.
                articles = group_stories(articles)
            if rich_first:
                # Google News links carry no photo, description or readable page; keep them, but last.
                articles.sort(key=lambda a: not (a["summarizable"] and a["image"]))
            feed = {"articles": articles, "fetchedAt": _now()}
        except NewsAPIError:
            stale = cache.get(f"stale:{key}")
            if stale is not None:
                log.warning("Serving stale copy of %s", key)
                return stale, True
            raise
        cache.set(key, feed, timeout=config["FEED_TTL"])
        cache.set(f"stale:{key}", feed, timeout=config["FEED_STALE_TTL"])
        return feed, False


def _cached_build(key, builder, locks=_LOCKS):
    """Like _cached_feed, for builders that pick their own TTL: builder() -> (value, ttl)."""
    hit = cache.get(key)
    if hit is not None:
        return hit
    with _lock_for(key, locks):
        hit = cache.get(key)
        if hit is None:
            hit, ttl = builder()
            cache.set(key, hit, timeout=ttl)
        return hit


def _edition():
    edition_id = (request.args.get("edition") or current_app.config["DEFAULT_EDITION"]).lower()
    edition = EDITIONS.get(edition_id)
    if not edition:
        raise APIError(400, "invalid_edition", f"Unknown edition. Choose one of: {', '.join(EDITIONS)}.")
    return edition


def _int_arg(name, default, low, high):
    try:
        value = int(request.args.get(name, default))
    except (TypeError, ValueError):
        raise APIError(400, "invalid_parameter", f"'{name}' must be a whole number.")
    return max(low, min(high, value))


def _page(feed, stale, **extra):
    offset = _int_arg("offset", 0, 0, 1000)
    limit = _int_arg("limit", 20, 1, 50)
    articles = feed["articles"]
    return jsonify(
        {
            **extra,
            "articles": articles[offset : offset + limit],
            "offset": offset,
            "limit": limit,
            "total": len(articles),
            "hasMore": offset + limit < len(articles),
            "fetchedAt": feed["fetchedAt"],
            "stale": stale,
        }
    )


def _headlines(edition, category):
    source = current_app.config["NEWS_SOURCE"]
    client = current_app.extensions["feed_client" if source == "rss" else "news_client"]
    return _cached_feed(
        f"feed:{source}:{edition.id}:{category}",
        lambda: client.top_headlines(edition, category),
        rich_first=True,
        group=True,
    )


def _signed_url(payload):
    """The article URL from a request body, if this server signed it; raises APIError otherwise."""
    url = payload.get("url")
    if not isinstance(url, str) or not url or len(url) > 2048:
        raise APIError(400, "invalid_url", "Send the article's url.")
    # Only links this server handed out are accepted, so these endpoints
    # can't be used as a free scraping or AI proxy.
    if not verify_url(current_app.config["SECRET_KEY"], url, payload.get("sig")):
        raise APIError(403, "invalid_signature", "This story can't be opened here. Refresh the page and try again.")
    return url


def _article(url):
    """Extracted article text, cached for follow-up questions and comparisons."""

    def build():
        try:
            return extract_article(url), ARTICLE_TTL
        except ExtractionError as exc:
            log.info("Extraction failed for %s: %s", url, exc.code)
            return {"failed": {"code": exc.code, "message": exc.message, "status": exc.status}}, FAILED_SUMMARY_TTL

    hit = _cached_build(f"article:{article_id(url)}", build, locks=_ARTICLE_LOCKS)
    if "failed" in hit:
        failure = hit["failed"]
        raise ExtractionError(failure["code"], failure["message"], failure["status"])
    return hit


def _source_name(article, url):
    return article.get("siteName") or (urlparse(url).hostname or "").removeprefix("www.")


@bp.get("/health")
def health():
    ai = current_app.extensions["ai"]
    return jsonify(
        {
            "status": "ok",
            "version": __version__,
            "newsConfigured": current_app.config["NEWS_SOURCE"] == "rss" or bool(current_app.config["NEWS_API_KEY"]),
            "newsSource": current_app.config["NEWS_SOURCE"],
            "searchSource": "newsapi" if current_app.config["NEWS_API_KEY"] else "feeds",
            "ai": {
                "enabled": ai is not None,
                "provider": ai.provider if ai else None,
                "model": ai.model if ai else None,
            },
            "defaultEdition": current_app.config["DEFAULT_EDITION"],
            "editions": [{"id": e.id, "label": e.label} for e in EDITIONS.values()],
            "categories": list(CATEGORIES),
        }
    )


@bp.get("/news")
def news():
    edition = _edition()
    category = (request.args.get("category") or "general").lower()
    if category not in CATEGORIES:
        raise APIError(400, "invalid_category", f"Unknown category. Choose one of: {', '.join(CATEGORIES)}.")
    feed, stale = _headlines(edition, category)
    return _page(feed, stale, edition=edition.id, category=category)


@bp.get("/search")
@limiter.limit(lambda: current_app.config["SEARCH_RATE_LIMIT"])
def search():
    edition = _edition()
    query = " ".join((request.args.get("q") or "").split())
    if not query:
        raise APIError(400, "missing_query", "Type something to search for.")
    if len(query) > 200:
        raise APIError(400, "query_too_long", "Search terms must be 200 characters or fewer.")
    sort = request.args.get("sort") or "publishedAt"
    if sort not in SORT_OPTIONS:
        raise APIError(400, "invalid_sort", f"Sort must be one of: {', '.join(SORT_OPTIONS)}.")

    if current_app.config["NEWS_API_KEY"]:
        client = current_app.extensions["news_client"]
        key = f"search:{edition.id}:{sort}:{query.lower()}"
        feed, stale = _cached_feed(key, lambda: client.search(query, edition, sort))
        return _page(feed, stale, edition=edition.id, query=query, sort=sort, searchSource="newsapi")

    key = f"search:local:{edition.id}:{sort}:{query.lower()}"
    feed = _cached_build(key, lambda: (_local_search(edition, query, sort), SEARCH_TTL))
    return _page(feed, False, edition=edition.id, query=query, sort=sort, searchSource="feeds")


def _local_search(edition, query, sort):
    """Search every section's current stories. All query words must match, else any of them."""
    pool, seen = [], set()
    for category in CATEGORIES:
        try:
            feed, _ = _headlines(edition, category)
        except NewsAPIError:
            continue
        for article in feed["articles"]:
            if article["id"] not in seen:
                seen.add(article["id"])
                pool.append(article)

    words = content_terms(query)
    phrase = query.lower()

    def score(article, need_all):
        title = content_terms(article["title"])
        text = title | content_terms(article["description"] or "")
        hits = words & text
        if not hits or (need_all and hits != words):
            return 0
        value = 3 * len(words & title) + len(hits)
        if phrase in article["title"].lower():
            value += 5
        return value

    for need_all in (True, False):
        matches = [(score(a, need_all), a) for a in pool]
        matches = [(s, a) for s, a in matches if s > 0]
        if matches:
            break
    if sort == "publishedAt":
        matches.sort(key=lambda pair: pair[1]["publishedAt"] or "", reverse=True)
    else:
        matches.sort(key=lambda pair: (pair[0], pair[1]["publishedAt"] or ""), reverse=True)
    return {"articles": [a for _, a in matches], "fetchedAt": _now()}


@bp.post("/summarize")
@limiter.limit(lambda: current_app.config["SUMMARIZE_RATE_LIMIT"])
def summarize():
    url = _signed_url(request.get_json(silent=True) or {})
    hit = _cached_build(f"summary:{article_id(url)}", lambda: _build_summary(url))
    if "failed" in hit:
        failure = hit["failed"]
        raise ExtractionError(failure["code"], failure["message"], failure["status"])
    return jsonify(hit)


def _build_summary(url):
    config = current_app.config
    ai = current_app.extensions["ai"]
    try:
        article = _article(url)
    except ExtractionError as exc:
        return {"failed": {"code": exc.code, "message": exc.message, "status": exc.status}}, FAILED_SUMMARY_TTL

    source = article["siteName"] or ""
    summary, mode, notice, truncated, ttl = None, "extractive", None, False, config["SUMMARY_TTL"]
    if ai:
        try:
            summary, truncated = ai.summarize(article["title"], source, article["text"])
            mode = "ai"
        except AIUnavailable as exc:
            log.warning("AI summary unavailable for %s: %s", url, exc)
            notice = "The AI summary isn't available right now, so here's a quick extractive summary."
            ttl = DEGRADED_TTL
    if summary is None:
        summary = extractive_summary(article["text"], title=article["title"])
    if summary is None:
        failure = {"code": "no_content", "message": "We couldn't summarize this article.", "status": 422}
        return {"failed": failure}, FAILED_SUMMARY_TTL

    summary_words = len(" ".join([summary["tldr"], *summary["keyPoints"], summary["whyItMatters"] or ""]).split())
    return {
        "url": url,
        "title": article["title"],
        "siteName": article["siteName"],
        "author": article["author"],
        "publishedAt": article["publishedAt"],
        "image": article["image"],
        "wordCount": article["wordCount"],
        "readingMinutes": reading_minutes(article["wordCount"]),
        "summaryWordCount": summary_words,
        "summary": summary,
        "mode": mode,
        "model": ai.model if mode == "ai" else None,
        "truncated": truncated,
        "notice": notice,
        "generatedAt": _now(),
    }, ttl


@bp.post("/ask")
@limiter.limit(lambda: current_app.config["ASK_RATE_LIMIT"])
def ask():
    payload = request.get_json(silent=True) or {}
    url = _signed_url(payload)
    question = " ".join(str(payload.get("question") or "").split())
    if len(question) < 3:
        raise APIError(400, "missing_question", "Type a question about this story.")
    if len(question) > 300:
        raise APIError(400, "question_too_long", "Questions must be 300 characters or fewer.")
    digest = hashlib.sha1(question.lower().encode()).hexdigest()[:16]
    return jsonify(_cached_build(f"ask:{article_id(url)}:{digest}", lambda: _build_answer(url, question)))


def _build_answer(url, question):
    config = current_app.config
    ai = current_app.extensions["ai"]
    article = _article(url)
    notice = None
    if ai:
        try:
            result = ai.ask(article["title"], _source_name(article, url), article["text"], question)
            return {"question": question, "mode": "ai", **result, "passages": [], "notice": None,
                    "generatedAt": _now()}, config["SUMMARY_TTL"]
        except AIUnavailable as exc:
            log.warning("AI answer unavailable for %s: %s", url, exc)
            notice = "The AI isn't available right now, so here are the passages that best match your question."
    passages = extractive_answer(article["text"], question)
    return {
        "question": question,
        "mode": "extractive",
        "answerable": bool(passages),
        "answer": None,
        "quote": None,
        "passages": passages,
        "notice": notice,
        "generatedAt": _now(),
    }, DEGRADED_ANSWER_TTL if notice else config["SUMMARY_TTL"]


@bp.post("/compare")
@limiter.limit(lambda: current_app.config["COMPARE_RATE_LIMIT"])
def compare():
    payload = request.get_json(silent=True) or {}
    stories = payload.get("stories")
    if not isinstance(stories, list) or not 2 <= len(stories) <= 4 or not all(isinstance(s, dict) for s in stories):
        raise APIError(400, "invalid_stories", "Send two to four stories to compare.")
    urls = [_signed_url(story) for story in stories]
    if len(set(urls)) != len(urls):
        raise APIError(400, "invalid_stories", "Each story can only be compared once.")
    key = "compare:" + hashlib.sha1("\n".join(sorted(urls)).encode()).hexdigest()[:20]
    hit = _cached_build(key, lambda: _build_comparison(urls))
    if "failed" in hit:
        failure = hit["failed"]
        raise APIError(failure["status"], failure["code"], failure["message"])
    return jsonify(hit)


def _build_comparison(urls):
    config = current_app.config
    ai = current_app.extensions["ai"]
    app = current_app._get_current_object()

    def load(url):
        with app.app_context():
            try:
                return _article(url)
            except ExtractionError:
                return None

    loaded = list(_ARTICLE_POOL.map(load, urls))
    readable = [(url, article) for url, article in zip(urls, loaded) if article]
    if len(readable) < 2:
        failure = {"code": "not_enough_text", "message": "We couldn't read enough of these stories to compare them.",
                   "status": 422}
        return {"failed": failure}, FAILED_SUMMARY_TTL

    items = [
        {"url": url, "source": _source_name(article, url), "title": article["title"] or "", "text": article["text"]}
        for url, article in readable
    ]
    base = [{"url": i["url"], "source": i["source"], "title": i["title"]} for i in items]
    common = {"skipped": len(urls) - len(readable), "generatedAt": _now()}
    notice = None
    if ai:
        try:
            result = ai.compare(items)
            outlets = [{**base[o["index"]], "angle": o["angle"], "unique": o["unique"]} for o in result["outlets"]]
            return {"mode": "ai", **result, "outlets": outlets, "notice": None, **common}, config["COMPARE_TTL"]
        except AIUnavailable as exc:
            log.warning("AI comparison unavailable: %s", exc)
            notice = "The AI isn't available right now, so here is how each outlet opens the story."

    outlets = []
    for entry, item in zip(base, items):
        summary = extractive_summary(item["text"], title=item["title"])
        outlets.append({**entry, "angle": summary["tldr"] if summary else None, "unique": []})
    return {
        "mode": "extractive",
        "sameEvent": None,
        "event": None,
        "commonGround": [],
        "outlets": outlets,
        "differences": [],
        "notice": notice,
        **common,
    }, DEGRADED_TTL if notice else config["COMPARE_TTL"]


@bp.get("/briefing")
def briefing():
    edition = _edition()
    ai = current_app.extensions["ai"]
    key = f"briefing:{edition.id}:{'ai' if ai else 'basic'}"
    return jsonify(_cached_build(key, lambda: _build_briefing(edition, ai)))


def _build_briefing(edition, ai):
    feed, _ = _headlines(edition, "general")
    candidates = feed["articles"][:20]
    ttl = current_app.config["BRIEFING_TTL"]
    if ai and candidates:
        try:
            result = ai.briefing(candidates)
            ai_ttl = getattr(ai, "briefing_ttl", None) or ttl
            return {"edition": edition.id, "mode": "ai", "generatedAt": _now(), **result}, ai_ttl
        except AIUnavailable as exc:
            log.warning("AI briefing unavailable: %s", exc)
            ttl = DEGRADED_TTL

    items = [
        {"article": a, "headline": a["title"], "summary": a["description"]}
        for a in candidates
        if a["description"]
    ][:5]
    return {"edition": edition.id, "mode": "headlines", "generatedAt": _now(), "intro": None, "items": items}, ttl
