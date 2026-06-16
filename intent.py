"""
intent.py — Simple keyword-based intent classifier.
Returns one of: "routing", "schedule", "fallback"
"""

import re

ROUTING_KEYWORDS = {
    "where", "location", "find", "reach", "how to get",
    "directions", "navigate", "path", "route", "go to",
    "way to", "nearest", "close to", "near",
    "map", "lost", "located", "get",   # covers "how do I get to X"
}

SCHEDULE_KEYWORDS = {
    "event", "events", "happening", "schedule", "day",
    "workshop", "workshops", "coding", "competition", "competitions",
    "what's on", "whats on", "what is on", "list", "show",
    "agenda", "programme", "program", "today", "tomorrow",
    "january", "jan", "when", "time", "slot", "session",
    "gaming", "cultural", "lecture", "talk",
}


def classify(query: str) -> str:
    """
    Classify query as 'routing', 'schedule', or 'fallback'.
    Strategy: check for routing keywords first (more specific),
    then schedule keywords.
    """
    lower = query.lower()
    tokens = set(re.findall(r"[a-z']+", lower))
    # Multi-word phrases
    for phrase in ("how to get", "way to", "whats on", "what's on", "what is on"):
        if phrase in lower:
            if phrase in {"how to get", "way to"}:
                return "routing"
            if phrase in {"whats on", "what's on", "what is on"}:
                return "schedule"

    if tokens & ROUTING_KEYWORDS:
        return "routing"
    if tokens & SCHEDULE_KEYWORDS:
        return "schedule"
    return "fallback"
