"""Group stories that cover the same event, so a feed shows one card per event.

Matching is lexical and runs locally. Two stories match when their headlines share two
content words and overlap strongly, or share three and their headline plus description
overlap moderately. Each group keeps one outlet per source.
"""

from datetime import datetime

from .summarizer import content_terms

MAX_GROUP = 5
WINDOW_SECONDS = 36 * 3600
TITLE_OVERLAP = 0.5
TEXT_JACCARD = 0.25


def _stamp(article):
    try:
        return datetime.fromisoformat(article["publishedAt"].replace("Z", "+00:00")).timestamp()
    except (AttributeError, TypeError, ValueError):
        return None


def _profile(article):
    title_terms = content_terms(article["title"])
    return {
        "article": article,
        "title": title_terms,
        "text": title_terms | content_terms(article.get("description") or ""),
        "stamp": _stamp(article),
    }


def same_story(a, b):
    shared = len(a["title"] & b["title"])
    if shared < 2:
        return False
    if shared / (min(len(a["title"]), len(b["title"])) or 1) >= TITLE_OVERLAP:
        return True
    if shared < 3:
        return False
    union = a["text"] | b["text"]
    return len(a["text"] & b["text"]) / len(union) >= TEXT_JACCARD


def _compact(article):
    return {
        key: article[key]
        for key in ("id", "title", "source", "url", "sig", "publishedAt", "summarizable")
    }


def group_stories(articles):
    """One entry per event, in feed order. Other outlets' versions go in `related`."""
    groups = []
    for article in articles:
        profile = _profile(article)
        home = None
        for group in groups:
            seed = group[0]
            if len(group) >= MAX_GROUP or any(m["article"]["source"] == article["source"] for m in group):
                continue
            if profile["stamp"] and seed["stamp"] and abs(profile["stamp"] - seed["stamp"]) > WINDOW_SECONDS:
                continue
            if same_story(profile, seed):
                home = group
                break
        if home is not None:
            home.append(profile)
        else:
            groups.append([profile])

    result = []
    for group in groups:
        members = [m["article"] for m in group]
        # Show the version with a photo and a readable page when there is one.
        lead = next((a for a in members if a["summarizable"] and a["image"]), members[0])
        if len(members) > 1:
            lead = {**lead, "related": [_compact(a) for a in members if a is not lead]}
        result.append(lead)
    return result
