"""BlitzFeed API: news headlines, article summaries, and daily briefings."""

import logging

from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

from .config import Config
from .errors import APIError
from .extensions import cache, limiter
from .extract import ExtractionError
from .feeds import FeedClient
from .news import NewsAPIError, NewsClient
from .ratebudget import RateBudget
from .summarizer import ClaudeSummarizer, GroqSummarizer

__version__ = "2.0.0"

log = logging.getLogger(__name__)


def _error(status, code, message):
    return jsonify({"error": {"code": code, "message": message}}), status


def _make_ai(config):
    """The AI brief writer for the configured provider, or None to use TextRank only."""
    provider = config["AI_PROVIDER"]
    if provider == "auto":
        provider = "anthropic" if config["ANTHROPIC_API_KEY"] else "groq" if config["GROQ_API_KEY"] else "off"

    if provider == "anthropic" and config["ANTHROPIC_API_KEY"]:
        return ClaudeSummarizer(
            config["ANTHROPIC_API_KEY"],
            config["ANTHROPIC_MODEL"],
            effort=config["ANTHROPIC_EFFORT"],
            timeout=config["ANTHROPIC_TIMEOUT"],
        )
    if provider == "groq" and config["GROQ_API_KEY"]:
        # Groq's limits cover the whole account, so split them across gunicorn processes.
        workers = max(1, config["WEB_CONCURRENCY"])
        budget = RateBudget(
            rpm=config["GROQ_RPM"],
            tpm=config["GROQ_TPM"],
            rpd=config["GROQ_RPD"],
            tpd=config["GROQ_TPD"],
            fraction=config["GROQ_LIMIT_FRACTION"] / workers,
            briefing_share=config["GROQ_BRIEFING_SHARE"],
            max_wait=config["GROQ_MAX_WAIT"],
        )
        return GroqSummarizer(
            config["GROQ_API_KEY"],
            config["GROQ_MODEL"],
            budget,
            reasoning_effort=config["GROQ_REASONING_EFFORT"],
            timeout=config["GROQ_TIMEOUT"],
            max_input_chars=config["GROQ_MAX_INPUT_CHARS"],
            briefing_ttl=config["GROQ_BRIEFING_TTL"],
        )
    if provider != "off":
        log.warning("AI_PROVIDER=%s needs its API key; using the built-in summarizer.", provider)
    return None


def create_app(overrides=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config.update(overrides or {})
    app.json.sort_keys = False

    logging.basicConfig(
        level=app.config["LOG_LEVEL"],
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if app.config["TRUST_PROXY"]:
        hops = app.config["TRUST_PROXY"]
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=hops, x_proto=hops)
    if app.config["CORS_ORIGINS"]:
        CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})

    cache.init_app(app)
    limiter.init_app(app)

    app.extensions["news_client"] = NewsClient(
        app.config["NEWS_API_KEY"], base_url=app.config["NEWS_API_BASE_URL"]
    )
    app.extensions["feed_client"] = FeedClient(stale_ttl=app.config["FEED_STALE_TTL"])
    if app.config.get("SECRET_KEY_ORIGIN") == "random":
        app.logger.warning("SECRET_KEY is not set; using a random one, so shared brief links break on restart.")
    ai = app.extensions["ai"] = _make_ai(app.config)
    if app.config["NEWS_SOURCE"] == "newsapi" and not app.config["NEWS_API_KEY"]:
        app.logger.warning("NEWS_SOURCE=newsapi but NEWS_API_KEY is not set; news endpoints will return 503.")
    app.logger.info(
        "Headlines from %s; search uses %s",
        "RSS feeds" if app.config["NEWS_SOURCE"] == "rss" else "NewsAPI",
        "NewsAPI" if app.config["NEWS_API_KEY"] else "the current feeds",
    )
    app.logger.info("AI summaries %s", f"enabled ({ai.provider}: {ai.model})" if ai else "disabled")

    from .routes import bp

    app.register_blueprint(bp)

    @app.errorhandler(APIError)
    @app.errorhandler(NewsAPIError)
    @app.errorhandler(ExtractionError)
    def handle_known_error(exc):
        if isinstance(exc, NewsAPIError):
            app.logger.warning("NewsAPI error %s: %s", exc.code, exc.message)
            # Don't leak upstream configuration details to the browser.
            message = (
                "The news provider is busy right now. Please try again in a few minutes."
                if exc.status == 503
                else "We couldn't load the news right now. Please try again shortly."
            )
            return _error(exc.status, exc.code, message)
        return _error(exc.status, exc.code, exc.message)

    @app.errorhandler(429)
    def handle_rate_limit(exc):
        return _error(429, "rate_limited", "You're going a little fast. Please wait a moment and try again.")

    @app.errorhandler(HTTPException)
    def handle_http_error(exc):
        return _error(exc.code, exc.name.lower().replace(" ", "_"), exc.description)

    @app.errorhandler(Exception)
    def handle_unexpected(exc):
        app.logger.exception("Unhandled error")
        return _error(500, "internal_error", "Something went wrong on our side.")

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Cache-Control", "no-store")
        return response

    return app
