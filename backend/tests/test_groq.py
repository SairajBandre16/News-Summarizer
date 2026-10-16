import json

import pytest
import requests
from requests.structures import CaseInsensitiveDict

from blitzfeed import create_app
from blitzfeed.ratebudget import BudgetExceeded, RateBudget, parse_duration
from blitzfeed.summarizer import AIUnavailable, GroqSummarizer

from .conftest import SAMPLE_TEXT

BRIEF = {
    "tldr": "The council approved a transit plan.",
    "keyPoints": ["Three new lines.", "Funded by sales tax."],
    "whyItMatters": "Commutes get shorter.",
    "sentiment": "positive",
    "topics": ["Transit"],
}


class FakeClock:
    def __init__(self):
        self.now = 1000.0
        self.slept = []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.now += seconds


def make_budget(clock=None, **overrides):
    clock = clock or FakeClock()
    options = dict(rpm=30, tpm=8000, rpd=1000, tpd=200_000, fraction=1.0, briefing_share=0.3, max_wait=0)
    options.update(overrides)
    return RateBudget(clock=clock, sleep=clock.sleep, **options), clock


class FakeResponse:
    def __init__(self, status=200, payload=None, headers=None):
        self.status_code = status
        self._payload = payload
        self.headers = CaseInsensitiveDict(headers or {})

    def json(self):
        if self._payload is None:
            raise ValueError("no body")
        return self._payload


class FakeSession:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def post(self, url, json=None, headers=None, timeout=None):
        self.calls.append({"url": url, "json": json, "headers": headers})
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def ok(content=BRIEF, total_tokens=900, headers=None):
    payload = {
        "id": "chatcmpl-1",
        "model": "openai/gpt-oss-120b",
        "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(content)}}],
        "usage": {"prompt_tokens": 600, "completion_tokens": 300, "total_tokens": total_tokens},
    }
    return FakeResponse(200, payload, headers)


def groq(session, budget=None, **options):
    budget = budget or make_budget()[0]
    return GroqSummarizer("gsk_test", "openai/gpt-oss-120b", budget, session=session, **options)


# Duration headers


@pytest.mark.parametrize(
    "value, seconds",
    [("12", 12), ("7.66s", 7.66), ("2m59.56s", 179.56), ("1h2m", 3720), ("120ms", 0.12), ("soon", None), (None, None)],
)
def test_parse_duration(value, seconds):
    result = parse_duration(value)
    assert result == pytest.approx(seconds) if seconds is not None else result is None


# RateBudget


def test_budget_refuses_over_tokens_per_minute_then_recovers():
    budget, clock = make_budget(tpm=5000)
    budget.acquire(3000)
    with pytest.raises(BudgetExceeded) as exc:
        budget.acquire(3000)
    assert exc.value.reason == "tokens per minute"
    clock.now += 61
    budget.acquire(3000)


def test_budget_never_accepts_a_call_bigger_than_the_minute_limit():
    budget, _ = make_budget(tpm=5000, max_wait=120)
    with pytest.raises(BudgetExceeded) as exc:
        budget.acquire(6000)
    assert exc.value.retry_in is None


def test_budget_waits_briefly_when_the_window_frees_soon():
    budget, clock = make_budget(tpm=5000, max_wait=5)
    budget.acquire(3000)
    clock.now += 57
    budget.acquire(3000)
    assert clock.slept and clock.slept[0] == pytest.approx(3.05)


def test_briefings_never_wait():
    budget, clock = make_budget(tpm=5000, max_wait=30)
    budget.acquire(3000)
    clock.now += 57
    with pytest.raises(BudgetExceeded):
        budget.acquire(3000, "briefing")
    assert clock.slept == []


def test_settle_returns_unused_tokens():
    budget, _ = make_budget(tpm=5000)
    budget.acquire(4000).settle(1000)
    budget.acquire(3500)
    assert budget.snapshot()["minute"]["tokens"] == 4500


def test_budget_applies_the_safety_fraction():
    budget, _ = make_budget(rpm=10, fraction=0.5)
    for _ in range(5):
        budget.acquire(10)
    with pytest.raises(BudgetExceeded):
        budget.acquire(10)


def test_daily_share_keeps_room_for_briefings():
    budget, clock = make_budget(tpd=10_000, briefing_share=0.3)
    for _ in range(7):
        budget.acquire(1000, "summary")
        clock.now += 61
    with pytest.raises(BudgetExceeded) as exc:
        budget.acquire(1000, "summary")
    assert exc.value.reason == "reader tokens per day"
    budget.acquire(1000, "briefing")
    clock.now += 86_400
    budget.acquire(1000, "summary")


def test_pause_blocks_until_it_ends():
    budget, clock = make_budget()
    budget.pause(30, "provider rate limit")
    with pytest.raises(BudgetExceeded) as exc:
        budget.acquire(100)
    assert exc.value.reason == "provider rate limit"
    clock.now += 31
    budget.acquire(100)


def test_budget_follows_provider_headers():
    budget, clock = make_budget(tpm=8000, rpd=1000)
    budget.observe_headers(
        CaseInsensitiveDict(
            {
                "x-ratelimit-limit-tokens": "6000",
                "x-ratelimit-limit-requests": "500",
                "x-ratelimit-remaining-tokens": "1500",
                "x-ratelimit-reset-tokens": "20s",
                "x-ratelimit-remaining-requests": "400",
                "x-ratelimit-reset-requests": "2h",
            }
        )
    )
    assert budget.tpm == 6000 and budget.rpd == 500
    with pytest.raises(BudgetExceeded) as exc:
        budget.acquire(2000)
    assert exc.value.reason == "provider tokens per minute"
    budget.acquire(1000)
    clock.now += 21
    budget.acquire(2000)


def test_budget_stops_when_provider_reports_no_requests_left():
    budget, clock = make_budget()
    budget.observe_headers({"x-ratelimit-remaining-requests": "0", "x-ratelimit-reset-requests": "1h"})
    with pytest.raises(BudgetExceeded) as exc:
        budget.acquire(100)
    assert exc.value.reason == "provider requests per day"
    clock.now += 3601
    budget.acquire(100)


# GroqSummarizer


def test_groq_summary_request_and_usage():
    budget, _ = make_budget()
    session = FakeSession(ok(total_tokens=900))
    summary, truncated = groq(session, budget).summarize("Transit plan", "Springfield Daily", SAMPLE_TEXT)

    assert summary["sentiment"] == "positive" and truncated is False
    body = session.calls[0]["json"]
    assert session.calls[0]["headers"]["authorization"] == "Bearer gsk_test"
    assert body["response_format"]["type"] == "json_schema"
    assert body["response_format"]["json_schema"]["strict"] is True
    assert body["reasoning_effort"] == "low" and body["include_reasoning"] is False
    assert body["max_completion_tokens"] == 800
    # The reservation is replaced by the real usage once the call returns.
    assert budget.snapshot()["day"]["reader"] == {"requests": 1, "tokens": 900}


def test_groq_output_uses_plain_punctuation():
    content = {**BRIEF, "tldr": "A long‑awaited plan passed at 9 p.m."}
    summary, _ = groq(FakeSession(ok(content))).summarize("T", "S", SAMPLE_TEXT)
    assert summary["tldr"] == "A long-awaited plan passed at 9 p.m."


def test_groq_clips_long_articles():
    session = FakeSession(ok())
    text = "A sentence about the transit plan. " * 1000
    _, truncated = groq(session, max_input_chars=2000).summarize("T", "S", text)
    assert truncated is True
    assert len(session.calls[0]["json"]["messages"][1]["content"]) < 2200


def test_groq_uses_json_mode_for_models_without_strict_schemas():
    budget, _ = make_budget()
    session = FakeSession(ok())
    GroqSummarizer("gsk_test", "llama-3.1-8b-instant", budget, session=session).summarize("T", "S", SAMPLE_TEXT)
    body = session.calls[0]["json"]
    assert body["response_format"] == {"type": "json_object"}
    assert "JSON schema" in body["messages"][0]["content"]
    assert "reasoning_effort" not in body


def test_groq_429_pauses_calls_without_retrying():
    budget, clock = make_budget()
    session = FakeSession(FakeResponse(429, {"error": {"message": "slow down"}}, {"retry-after": "20"}), ok())
    writer = groq(session, budget)
    with pytest.raises(AIUnavailable, match="rate limited"):
        writer.summarize("T", "S", SAMPLE_TEXT)
    with pytest.raises(AIUnavailable, match="over budget"):
        writer.summarize("T", "S", SAMPLE_TEXT)
    assert len(session.calls) == 1
    clock.now += 21
    writer.summarize("T", "S", SAMPLE_TEXT)
    assert len(session.calls) == 2


def test_groq_bad_key_stops_calls_for_an_hour():
    budget, clock = make_budget()
    session = FakeSession(FakeResponse(401, {"error": {"message": "Invalid API Key"}}))
    writer = groq(session, budget)
    with pytest.raises(AIUnavailable):
        writer.summarize("T", "S", SAMPLE_TEXT)
    clock.now += 600
    with pytest.raises(AIUnavailable, match="over budget"):
        writer.summarize("T", "S", SAMPLE_TEXT)
    assert len(session.calls) == 1


def test_groq_connection_error_falls_back():
    session = FakeSession(requests.ConnectionError("down"))
    with pytest.raises(AIUnavailable, match="connection error"):
        groq(session).summarize("T", "S", SAMPLE_TEXT)


@pytest.mark.parametrize(
    "content, finish, error",
    [
        ({"tldr": "Only a tldr"}, "stop", "match the schema"),
        ({**BRIEF, "sentiment": "angry"}, "stop", "match the schema"),
        (BRIEF, "length", "truncated"),
    ],
)
def test_groq_rejects_bad_output(content, finish, error):
    response = ok(content)
    response._payload["choices"][0]["finish_reason"] = finish
    with pytest.raises(AIUnavailable, match=error):
        groq(FakeSession(response)).summarize("T", "S", SAMPLE_TEXT)


def test_groq_briefing_uses_the_briefing_share():
    budget, _ = make_budget()
    articles = [{"title": f"Story {n}", "source": "Wire", "description": "x" * 500} for n in range(1, 8)]
    content = {"intro": "Busy day.", "items": [{"index": 2, "headline": "H", "summary": "S"}]}
    session = FakeSession(ok(content, total_tokens=1200))
    result = groq(session, budget).briefing(articles)
    assert result["items"][0]["article"]["title"] == "Story 2"
    assert session.calls[0]["json"]["max_completion_tokens"] == 1200
    assert "x" * 281 not in session.calls[0]["json"]["messages"][1]["content"]
    assert budget.snapshot()["day"]["briefing"]["tokens"] == 1200


# App wiring


def _app(**config):
    base = {"TESTING": True, "NEWS_API_KEY": "k", "SECRET_KEY": "s", "ANTHROPIC_API_KEY": "", "GROQ_API_KEY": ""}
    return create_app({**base, **config})


def test_groq_is_picked_when_it_is_the_only_key():
    app = _app(GROQ_API_KEY="gsk_test", WEB_CONCURRENCY=2, GROQ_LIMIT_FRACTION=0.8, GROQ_TPM=8000)
    ai = app.extensions["ai"]
    assert ai.provider == "groq" and ai.briefing_ttl == 3600
    # Two gunicorn processes share the account's limits.
    assert ai.budget.tpm == pytest.approx(3200)
    health = app.test_client().get("/api/health").get_json()
    assert health["ai"] == {"enabled": True, "provider": "groq", "model": "openai/gpt-oss-120b"}


def test_ai_provider_off_and_missing_key():
    assert _app(GROQ_API_KEY="gsk_test", AI_PROVIDER="off").extensions["ai"] is None
    assert _app(AI_PROVIDER="groq").extensions["ai"] is None
    assert _app(ANTHROPIC_API_KEY="sk-ant", GROQ_API_KEY="gsk_test").extensions["ai"].provider == "anthropic"


def test_secret_key_is_never_a_public_default(monkeypatch):
    from blitzfeed import config

    for name in ("SECRET_KEY", "NEWS_API_KEY", "GROQ_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.setenv(name, "")
    first, origin = config._secret_key()
    second, _ = config._secret_key()
    assert origin == "random" and first != second

    monkeypatch.setenv("GROQ_API_KEY", "gsk_private")
    derived, origin = config._secret_key()
    assert origin == "derived" and derived == config._secret_key()[0]

    monkeypatch.setenv("SECRET_KEY", "explicit")
    assert config._secret_key() == ("explicit", "env")
