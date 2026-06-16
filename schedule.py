"""
schedule.py — Query the events DB, parse day/date from natural language,
support category follow-up filters.
"""

import re
from typing import Optional
from sqlalchemy.orm import Session
from models import Event

# ---------------------------------------------------------------------------
# Day-number extraction
# ---------------------------------------------------------------------------
# Shaastra 2025 dates: Day1=Jan16, Day2=Jan17, Day3=Jan18, Day4=Jan19
DATE_TO_DAY = {
    "16": 1, "january 16": 1, "jan 16": 1,
    "17": 2, "january 17": 2, "jan 17": 2,
    "18": 3, "january 18": 3, "jan 18": 3,
    "19": 4, "january 19": 4, "jan 19": 4,
}

DAY_ORDINALS = {
    "1": 1, "first": 1, "one": 1,
    "2": 2, "second": 2, "two": 2,
    "3": 3, "third": 3, "three": 3,
    "4": 4, "fourth": 4, "four": 4,
}

CATEGORY_KEYWORDS = {
    "workshop": "workshop",
    "workshops": "workshop",
    "coding": "coding",
    "code": "coding",
    "hackathon": "coding",
    "competitive": "coding",
    "programming": "coding",
    "cultural": "cultural",
    "band": "cultural",
    "music": "cultural",
    "performance": "cultural",
    "lecture": "lecture",
    "talk": "lecture",
    "keynote": "lecture",
    "panel": "lecture",
    "gaming": "gaming",
    "game": "gaming",
    "drone": "gaming",
}


def _extract_day(query: str) -> Optional[int]:
    lower = query.lower()

    # "day 2", "day two", "day2"
    m = re.search(r"day[\s#\-]*([a-z0-9]+)", lower)
    if m:
        tok = m.group(1).strip()
        if tok in DAY_ORDINALS:
            return DAY_ORDINALS[tok]

    # "january 17" / "jan 17" / bare date "17"
    for phrase, day in sorted(DATE_TO_DAY.items(), key=lambda x: -len(x[0])):
        if phrase in lower:
            return day

    # "2nd day" / "second day"
    m = re.search(r"([a-z0-9]+)\s*(st|nd|rd|th)?\s*day", lower)
    if m:
        tok = m.group(1)
        if tok in DAY_ORDINALS:
            return DAY_ORDINALS[tok]

    return None


def _extract_category(query: str) -> Optional[str]:
    lower = query.lower()
    for kw, cat in CATEGORY_KEYWORDS.items():
        if kw in lower:
            return cat
    return None


def _group_by_time(events: list[Event]) -> dict:
    """Group a list of Events by start_time, sorted."""
    groups: dict[str, list] = {}
    for ev in sorted(events, key=lambda e: e.start_time):
        groups.setdefault(ev.start_time, []).append(ev.to_dict())
    return groups


def query_schedule(db: Session, query: str, category_override: Optional[str] = None) -> dict:
    """
    Parse query for day + optional category, return matching events.
    Returns:
      {
        day_number: int | None,
        category: str | None,
        grouped: {time_slot: [event_dict, ...]},
        total: int,
        message: str,
      }
    """
    day = _extract_day(query)
    category = category_override or _extract_category(query)

    q = db.query(Event)
    if day:
        q = q.filter(Event.day_number == day)
    if category:
        q = q.filter(Event.category == category)

    results: list[Event] = q.order_by(Event.day_number, Event.start_time).all()

    if not results:
        parts = []
        if day:
            parts.append(f"Day {day}")
        if category:
            parts.append(f"category '{category}'")
        qualifier = " + ".join(parts) if parts else "any filter"
        message = f"No events found for {qualifier}. Try a different day or category."
    else:
        day_label = f"Day {day}" if day else "all days"
        cat_label  = f" [{category}]" if category else ""
        message = f"Found {len(results)} event(s) for {day_label}{cat_label}."

    grouped = _group_by_time(results) if results else {}

    return {
        "day_number": day,
        "category":   category,
        "grouped":    grouped,
        "total":      len(results),
        "message":    message,
    }


def list_categories(db: Session) -> list[str]:
    rows = db.query(Event.category).distinct().all()
    return sorted(r[0] for r in rows)


def all_days_summary(db: Session) -> dict:
    """Return a count of events per day."""
    from sqlalchemy import func
    rows = db.query(Event.day_number, func.count(Event.id)).group_by(Event.day_number).all()
    return {f"Day {r[0]}": r[1] for r in sorted(rows)}
