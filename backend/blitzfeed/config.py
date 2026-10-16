"""Runtime configuration, read from environment variables (and .env files)."""

import hashlib
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent

# backend/.env wins; the repo-root .env is still read so older setups keep working.
load_dotenv(BACKEND_DIR / ".env")
load_dotenv(BACKEND_DIR.parent / ".env")

# Models that accept the server-side refusal fallback (`fallbacks: "default"`).
FALLBACK_CAPABLE_MODELS = (
    "claude-fable-5-1",
    "claude-opus-5-5",
    "claude-opus-5",
    "claude-sonnet-5-5",
)


def _env(name, default=""):
    return os.getenv(name, default).strip()


def _int(name, default):
    try:
        return int(_env(name, str(default)))
    except ValueError:
        return default


def _float(name, default):
    try:
        return float(_env(name, str(default)))
    except ValueError:
        return default


def _secret_key():
    """(key, origin) for signing article links. origin is "env", "derived" or "random"."""
    explicit = _env("SECRET_KEY")
    if explicit:
        return explicit, "env"
    # Derive from a private API key so every worker, and every restart, signs links the same way.
    private = _env("NEWS_API_KEY") or _env("GROQ_API_KEY") or _env("ANTHROPIC_API_KEY")
    if private:
        return hashlib.sha256(f"blitzfeed:{private}".encode()).hexdigest(), "derived"
    # Nothing private to derive from. A public default would let anyone forge links, so use a
    # random key; shared brief links then stop working when the server restarts.
    return secrets.token_hex(32), "random"


class Config:
    # Headlines come from publishers' RSS feeds ("rss", no key needed) or NewsAPI ("newsapi").
    NEWS_SOURCE = "newsapi" if _env("NEWS_SOURCE").lower() == "newsapi" else "rss"
    # Optional with RSS: when set, search covers all of NewsAPI instead of the current feeds.
    NEWS_API_KEY = _env("NEWS_API_KEY")
    NEWS_API_BASE_URL = _env("NEWS_API_BASE_URL", "https://newsapi.org/v2")

    # AI briefs: "auto" uses Claude when ANTHROPIC_API_KEY is set, otherwise Groq when
    # GROQ_API_KEY is set, otherwise the built-in TextRank summarizer. "off" forces TextRank.
    AI_PROVIDER = _env("AI_PROVIDER", "auto").lower()

    ANTHROPIC_API_KEY = _env("ANTHROPIC_API_KEY")
    ANTHROPIC_MODEL = _env("ANTHROPIC_MODEL", "claude-opus-5-5")
    ANTHROPIC_EFFORT = _env("ANTHROPIC_EFFORT", "low")
    ANTHROPIC_TIMEOUT = _int("ANTHROPIC_TIMEOUT", 45)

    GROQ_API_KEY = _env("GROQ_API_KEY")
    GROQ_MODEL = _env("GROQ_MODEL", "openai/gpt-oss-120b")
    GROQ_REASONING_EFFORT = _env("GROQ_REASONING_EFFORT", "low")
    GROQ_TIMEOUT = _int("GROQ_TIMEOUT", 30)
    # Article text sent per brief. Groq's free plan allows ~8K tokens a minute, so keep this small.
    GROQ_MAX_INPUT_CHARS = _int("GROQ_MAX_INPUT_CHARS", 6000)
    # Groq's published free-plan limits for the model. BlitzFeed plans against
    # GROQ_LIMIT_FRACTION of them and also follows the limits Groq reports in its headers.
    GROQ_RPM = _int("GROQ_RPM", 30)
    GROQ_TPM = _int("GROQ_TPM", 8000)
    GROQ_RPD = _int("GROQ_RPD", 1000)
    GROQ_TPD = _int("GROQ_TPD", 200_000)
    GROQ_LIMIT_FRACTION = _float("GROQ_LIMIT_FRACTION", 0.8)
    # Share of the daily budget kept for the "Today in 60 seconds" briefing.
    GROQ_BRIEFING_SHARE = _float("GROQ_BRIEFING_SHARE", 0.3)
    # Seconds a brief, answer or comparison may wait for the per-minute window before falling back.
    GROQ_MAX_WAIT = _float("GROQ_MAX_WAIT", 10)
    GROQ_BRIEFING_TTL = _int("GROQ_BRIEFING_TTL", 3600)
    # gunicorn processes; each gets an equal slice of the Groq budget.
    WEB_CONCURRENCY = _int("WEB_CONCURRENCY", 1)

    SECRET_KEY, SECRET_KEY_ORIGIN = _secret_key()
    DEFAULT_EDITION = _env("DEFAULT_EDITION", "us")

    # Caching: SimpleCache (in-process) by default, RedisCache when REDIS_URL is set.
    CACHE_TYPE = "RedisCache" if _env("REDIS_URL") else "SimpleCache"
    CACHE_REDIS_URL = _env("REDIS_URL") or None
    CACHE_THRESHOLD = 2000
    CACHE_DEFAULT_TIMEOUT = 900
    FEED_TTL = _int("FEED_TTL", 900)
    FEED_STALE_TTL = _int("FEED_STALE_TTL", 86400)
    SUMMARY_TTL = _int("SUMMARY_TTL", 86400)
    BRIEFING_TTL = _int("BRIEFING_TTL", 1800)
    COMPARE_TTL = _int("COMPARE_TTL", 6 * 3600)

    # Rate limiting only guards the endpoints that cost money or quota.
    RATELIMIT_STORAGE_URI = _env("RATELIMIT_STORAGE_URI", _env("REDIS_URL") or "memory://")
    RATELIMIT_HEADERS_ENABLED = True
    SUMMARIZE_RATE_LIMIT = _env("SUMMARIZE_RATE_LIMIT", "15/minute;300/day")
    SEARCH_RATE_LIMIT = _env("SEARCH_RATE_LIMIT", "30/minute")
    ASK_RATE_LIMIT = _env("ASK_RATE_LIMIT", "8/minute;80/day")
    COMPARE_RATE_LIMIT = _env("COMPARE_RATE_LIMIT", "6/minute;60/day")

    # Comma-separated origins allowed to call the API directly from a browser.
    # Leave empty when the Next.js app proxies /api (the default setup).
    CORS_ORIGINS = [o.strip() for o in _env("CORS_ORIGINS").split(",") if o.strip()]
    # Number of reverse proxies in front of the API (e.g. 1 for the Next.js proxy).
    TRUST_PROXY = _int("TRUST_PROXY", 0)

    LOG_LEVEL = _env("LOG_LEVEL", "INFO").upper()
