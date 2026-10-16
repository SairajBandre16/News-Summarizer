"""Client-side rate budget for an AI provider with tight limits (Groq's free plan).

Every call reserves its estimated tokens before it is sent. A call that doesn't fit the
per-minute or per-day windows is refused here, so the app falls back to its own summarizer
instead of collecting 429s. The provider's rate-limit headers and 429 responses pause calls
until the provider says there is room again.

The windows live in this process. gunicorn runs one process by default; with more, give
each one a share of the limits (create_app divides them by WEB_CONCURRENCY).
"""

import re
import threading
import time
from collections import deque

MINUTE = 60
DAY = 86_400

_DURATION_RE = re.compile(r"(\d+(?:\.\d+)?)(ms|h|m|s)")
_UNIT_SECONDS = {"h": 3600, "m": 60, "s": 1, "ms": 0.001}


def parse_duration(value):
    """Seconds from a header such as "12", "7.66s", "2m59.56s", "1h2m" or "120ms"; None if unreadable."""
    if value is None:
        return None
    value = str(value).strip()
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    parts = _DURATION_RE.findall(value)
    if not parts or "".join(number + unit for number, unit in parts) != value:
        return None
    return sum(float(number) * _UNIT_SECONDS[unit] for number, unit in parts)


def _number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class BudgetExceeded(Exception):
    def __init__(self, reason, retry_in=None):
        super().__init__(reason)
        self.reason = reason
        self.retry_in = retry_in


def pool_for(kind):
    """The daily briefing has its own pool; briefs, questions and comparisons share the reader pool."""
    return "briefing" if kind == "briefing" else "reader"


class Reservation:
    """Tokens held for one call. settle() swaps the estimate for the real usage."""

    def __init__(self, budget, entry):
        self._budget = budget
        self._entry = entry

    def settle(self, tokens):
        with self._budget._lock:
            self._entry[1] = max(0, int(tokens))


class RateBudget:
    def __init__(
        self,
        *,
        rpm,
        tpm,
        rpd,
        tpd,
        fraction=0.8,
        briefing_share=0.3,
        max_wait=5.0,
        clock=time.monotonic,
        sleep=time.sleep,
    ):
        # Plan against a fraction of the provider's limits to leave headroom for estimate errors.
        self.fraction = min(1.0, max(0.01, fraction))
        self.rpm = rpm * self.fraction
        self.tpm = tpm * self.fraction
        self.rpd = rpd * self.fraction
        self.tpd = tpd * self.fraction
        # Share of the daily budget kept for briefings; reader features (briefs, questions,
        # comparisons) share the rest.
        self.briefing_share = min(1.0, max(0.0, briefing_share))
        self.max_wait = max(0.0, max_wait)
        self._clock = clock
        self._sleep = sleep
        self._lock = threading.Lock()
        self._events = deque()  # [monotonic time, tokens, pool], oldest first
        self._pause_until = 0.0
        self._pause_reason = None
        # What the provider last reported: (remaining, monotonic reset time).
        self._server_tokens = (None, 0.0)
        self._server_requests = (None, 0.0)

    def acquire(self, tokens, kind="summary"):
        """Reserve `tokens` for one call, waiting up to max_wait for room. Raises BudgetExceeded.

        Briefings never wait: the page shows plain headlines instead. Someone waiting on a
        brief, answer or comparison would rather wait a few seconds than get a fallback.
        """
        deadline = self._clock() + (0 if pool_for(kind) == "briefing" else self.max_wait)
        while True:
            with self._lock:
                now = self._clock()
                self._prune(now)
                wait, reason = self._check(now, tokens, kind)
                if wait == 0:
                    entry = [now, tokens, pool_for(kind)]
                    self._events.append(entry)
                    self._spend_server_view(now, tokens)
                    return Reservation(self, entry)
            if wait is None or now + wait > deadline:
                raise BudgetExceeded(reason, wait)
            self._sleep(wait + 0.05)

    def pause(self, seconds, reason="provider asked us to wait"):
        with self._lock:
            until = self._clock() + max(0.0, seconds)
            if until > self._pause_until:
                self._pause_until, self._pause_reason = until, reason

    def observe_headers(self, headers):
        """Follow the provider's x-ratelimit-* headers (Groq: requests per day, tokens per minute)."""
        with self._lock:
            now = self._clock()
            limit_tokens = _number(headers.get("x-ratelimit-limit-tokens"))
            limit_requests = _number(headers.get("x-ratelimit-limit-requests"))
            # Adopt the provider's limits when they are tighter than the configured ones.
            if limit_tokens:
                self.tpm = min(self.tpm, limit_tokens * self.fraction)
            if limit_requests:
                self.rpd = min(self.rpd, limit_requests * self.fraction)

            tokens_left = _number(headers.get("x-ratelimit-remaining-tokens"))
            tokens_reset = parse_duration(headers.get("x-ratelimit-reset-tokens"))
            if tokens_left is not None and tokens_reset is not None:
                self._server_tokens = (tokens_left, now + tokens_reset)
            requests_left = _number(headers.get("x-ratelimit-remaining-requests"))
            requests_reset = parse_duration(headers.get("x-ratelimit-reset-requests"))
            if requests_left is not None and requests_reset is not None:
                self._server_requests = (requests_left, now + requests_reset)

    def snapshot(self):
        with self._lock:
            now = self._clock()
            self._prune(now)
            minute = [e for e in self._events if e[0] > now - MINUTE]
            return {
                "minute": {"requests": len(minute), "tokens": sum(e[1] for e in minute)},
                "day": {
                    pool: {
                        "requests": sum(1 for e in self._events if e[2] == pool),
                        "tokens": sum(e[1] for e in self._events if e[2] == pool),
                    }
                    for pool in ("reader", "briefing")
                },
                "pausedFor": max(0.0, self._pause_until - now),
            }

    # Internals; callers hold self._lock.

    def _prune(self, now):
        while self._events and self._events[0][0] <= now - DAY:
            self._events.popleft()

    def _check(self, now, tokens, kind):
        """(0, None) when the call fits now, (seconds, reason) when it will fit later, (None, reason) if never."""
        waits = []
        if now < self._pause_until:
            waits.append((self._pause_until - now, self._pause_reason))
        left, reset_at = self._server_tokens
        if left is not None and now < reset_at and tokens > left:
            waits.append((reset_at - now, "provider tokens per minute"))
        left, reset_at = self._server_requests
        if left is not None and now < reset_at and left < 1:
            waits.append((reset_at - now, "provider requests per day"))

        pool = pool_for(kind)
        share = self.briefing_share if pool == "briefing" else 1.0 - self.briefing_share
        windows = (
            (MINUTE, self.rpm, False, None, "requests per minute"),
            (MINUTE, self.tpm, True, None, "tokens per minute"),
            (DAY, self.rpd * share, False, pool, f"{pool} requests per day"),
            (DAY, self.tpd * share, True, pool, f"{pool} tokens per day"),
        )
        for window, limit, count_tokens, only_pool, reason in windows:
            cost = tokens if count_tokens else 1
            wait = self._wait_for(now, window, limit, cost, count_tokens=count_tokens, pool=only_pool)
            if wait is None:
                return None, reason
            if wait:
                waits.append((wait, reason))
        return max(waits, key=lambda w: w[0]) if waits else (0, None)

    def _wait_for(self, now, window, limit, cost, *, count_tokens, pool):
        """Seconds until `cost` more fits under `limit` in the trailing window; 0 if now, None if never."""
        if cost > limit:
            return None
        entries = [e for e in self._events if e[0] > now - window and (pool is None or e[2] == pool)]
        weight = (lambda e: e[1]) if count_tokens else (lambda e: 1)
        used = sum(weight(e) for e in entries)
        if used + cost <= limit:
            return 0
        for entry in entries:
            used -= weight(entry)
            if used + cost <= limit:
                return entry[0] + window - now
        return window

    def _spend_server_view(self, now, tokens):
        left, reset_at = self._server_tokens
        if left is not None and now < reset_at:
            self._server_tokens = (left - tokens, reset_at)
        left, reset_at = self._server_requests
        if left is not None and now < reset_at:
            self._server_requests = (left - 1, reset_at)
