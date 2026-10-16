from blitzfeed.summarizer import extractive_summary, key_phrases, reading_minutes, split_sentences

from .conftest import SAMPLE_TEXT


def test_split_sentences_respects_abbreviations():
    text = "Dr. Smith met Mr. Jones in the U.S. Capitol on Monday. They talked for an hour. Then J. Doe left!"
    assert split_sentences(text) == [
        "Dr. Smith met Mr. Jones in the U.S. Capitol on Monday.",
        "They talked for an hour.",
        "Then J. Doe left!",
    ]


def test_split_sentences_handles_quotes_and_paragraphs():
    text = '"We won," she said. The crowd cheered.\nA new paragraph starts here.'
    assert split_sentences(text) == ['"We won," she said.', "The crowd cheered.", "A new paragraph starts here."]


def test_extractive_summary_picks_central_sentences():
    summary = extractive_summary(SAMPLE_TEXT, title="Council approves $2.4 billion transit plan")
    assert "transit plan" in summary["tldr"].lower()
    assert 1 <= len(summary["keyPoints"]) <= 4
    assert summary["tldr"] not in summary["keyPoints"]
    assert summary["sentiment"] is None and summary["whyItMatters"] is None


def test_extractive_summary_returns_none_for_tiny_text():
    assert extractive_summary("Too short.") is None


def test_key_phrases_find_recurring_names():
    phrases = key_phrases(split_sentences(SAMPLE_TEXT))
    assert "Dana Ortiz" in phrases
    assert "Springfield Transit Plan" in phrases
    assert "Tuesday" not in phrases


def test_reading_minutes():
    assert reading_minutes(10) == 1
    assert reading_minutes(1150) == 5
