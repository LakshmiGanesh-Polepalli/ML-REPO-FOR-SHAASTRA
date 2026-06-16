"""
main.py — FastAPI backend for Shaastra chatbot.
Endpoint: POST /query  { query, lat?, lng? }
"""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

import re

from intent import classify
from graph import (
    find_path, nearest_node, all_nodes_svg, all_edges_svg,
    NODES, get_node_info
)
from schedule import query_schedule, list_categories, all_days_summary
from models import get_db, create_tables
from seed import seed

# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
app = FastAPI(title="Shaastra Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    try:
        create_tables()
        seed()
    except Exception as e:
        print(f"[startup] DB init warning: {e}")


# ---------------------------------------------------------------------------
# Fuzzy location extraction using rapidfuzz
# ---------------------------------------------------------------------------
try:
    from rapidfuzz import process, fuzz
    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False
    print("rapidfuzz not installed — falling back to exact substring matching.")

LOCATION_NAMES = list(NODES.keys())
LOCATION_ALIASES = {
    "open air theatre":       "OAT",
    "open air":               "OAT",
    "central lecture theatre":"CLT",
    "central lecture":        "CLT",
    "student activity centre":"SAC",
    "student activity":       "SAC",
    "himalaya":               "Himalaya",
    "godavari":               "Godavari",
    "jamuna":                 "Jamuna",
    "sharavati":              "Sharavati",
    "taramani":               "Taramani Gate",
    "main gate":              "Main Gate",
    "main entrance":          "Main Gate",
    "taramani gate":          "Taramani Gate",
}


def extract_location(text: str) -> Optional[str]:
    """Extract a campus location name from free text using fuzzy matching."""
    lower = text.lower()

    # 1. Alias check (exact substring)
    for alias, node in sorted(LOCATION_ALIASES.items(), key=lambda x: -len(x[0])):
        if alias in lower:
            return node

    # 2. Exact node name substring
    for name in LOCATION_NAMES:
        if name.lower() in lower:
            return name

    # 3. rapidfuzz fuzzy match on individual tokens / short spans
    if HAS_RAPIDFUZZ:
        # Try matching words/bigrams from the query against node names
        words = re.findall(r"[a-zA-Z]+", text)
        candidates = [" ".join(words[i:i+3]) for i in range(len(words))]
        candidates += words
        best_match, best_score = None, 0
        for cand in candidates:
            match = process.extractOne(
                cand, LOCATION_NAMES,
                scorer=fuzz.token_sort_ratio,
                score_cutoff=72,
            )
            if match and match[1] > best_score:
                best_score = match[1]
                best_match = match[0]
        if best_match:
            return best_match

    return None


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------
class QueryRequest(BaseModel):
    query: str
    lat: Optional[float] = None
    lng: Optional[float] = None


class QueryResponse(BaseModel):
    intent:      str
    message:     str
    # routing fields
    path:        Optional[list]   = None
    directions:  Optional[list]   = None
    total_dist:  Optional[int]    = None
    svg_path:    Optional[list]   = None   # [{x,y}] for frontend
    origin_node: Optional[str]    = None
    dest_node:   Optional[str]    = None
    # schedule fields
    day_number:  Optional[int]    = None
    category:    Optional[str]    = None
    grouped:     Optional[dict]   = None
    total_events:Optional[int]    = None
    # map data (always sent)
    map_nodes:   Optional[list]   = None
    map_edges:   Optional[list]   = None


# ---------------------------------------------------------------------------
# Helper — strip routing prepositions to isolate destination
# ---------------------------------------------------------------------------
def extract_destination_from_routing_query(query: str) -> Optional[str]:
    # Remove common lead-in phrases so fuzzy match focuses on the location
    cleaned = re.sub(
        r"(?i)(how (do i|can i|to)?\s*(get|reach|go)\s*(to|from)?|"
        r"where (is|are|can i find)?|"
        r"find|navigate to|route to|directions? to|"
        r"take me to|i want to go to|locate|nearest|"
        r"location of|show me|i am at|i('?m| am) (at|near)?)",
        " ", query
    )
    return extract_location(cleaned) or extract_location(query)


# ---------------------------------------------------------------------------
# Main endpoint
# ---------------------------------------------------------------------------
@app.post("/query", response_model=QueryResponse)
def handle_query(req: QueryRequest, db: Session = Depends(get_db)):
    intent = classify(req.query)
    map_nodes = all_nodes_svg()
    map_edges = all_edges_svg()
    base = {"map_nodes": map_nodes, "map_edges": map_edges}

    # ── ROUTING ─────────────────────────────────────────────────────────────
    if intent == "routing":
        # Origin: from geolocation or mentioned in query
        origin = None
        # Check if the query mentions "from <place>"
        from_match = re.search(r"(?i)from\s+(.+?)\s+to\b", req.query)
        if from_match:
            origin = extract_location(from_match.group(1))

        if origin is None:
            if req.lat is not None and req.lng is not None:
                origin = nearest_node(req.lat, req.lng)
            else:
                origin = "Main Gate"  # sensible campus default

        destination = extract_destination_from_routing_query(req.query)

        if destination is None:
            return QueryResponse(
                intent="routing",
                message=(
                    "I couldn't figure out your destination. "
                    "Try: 'Where is OAT?' or 'How do I get to CLT?'"
                ),
                **base,
            )

        if origin == destination:
            node = get_node_info(destination)
            return QueryResponse(
                intent="routing",
                message=f"You're already at **{node['display']}** — {node['desc']}.",
                path=[destination],
                directions=[f"You are already at {node['display']}!"],
                total_dist=0,
                svg_path=[{"x": node["svg_x"], "y": node["svg_y"]}],
                origin_node=origin,
                dest_node=destination,
                **base,
            )

        result = find_path(origin, destination)
        if result.get("error"):
            return QueryResponse(
                intent="routing",
                message=result["error"],
                **base,
            )

        dest_info = get_node_info(destination)
        summary = (
            f"📍 Route from **{NODES[origin]['display']}** → "
            f"**{dest_info['display']}** "
            f"({result['total_dist']}m walking)"
        )

        return QueryResponse(
            intent="routing",
            message=summary,
            path=result["path"],
            directions=result["directions"],
            total_dist=result["total_dist"],
            svg_path=result["svg_coords"],
            origin_node=origin,
            dest_node=destination,
            **base,
        )

    # ── SCHEDULE ─────────────────────────────────────────────────────────────
    if intent == "schedule":
        result = query_schedule(db, req.query)
        return QueryResponse(
            intent="schedule",
            message=result["message"],
            day_number=result["day_number"],
            category=result["category"],
            grouped=result["grouped"],
            total_events=result["total"],
            **base,
        )

    # ── FALLBACK ─────────────────────────────────────────────────────────────
    return QueryResponse(
        intent="fallback",
        message=(
            "👋 Hi! I'm the Shaastra 2025 assistant. I can help with:\n\n"
            "🗺️ **Navigation** — e.g. 'Where is OAT?', 'How do I get to CLT?'\n"
            "📅 **Schedule** — e.g. 'What events are on Day 2?', "
            "'Show me workshops on January 17'\n\n"
            "What would you like to know?"
        ),
        **base,
    )


# ---------------------------------------------------------------------------
# Utility endpoints
# ---------------------------------------------------------------------------
@app.get("/map")
def get_map_data():
    return {"nodes": all_nodes_svg(), "edges": all_edges_svg()}


@app.get("/events/summary")
def events_summary(db: Session = Depends(get_db)):
    return {
        "days":       all_days_summary(db),
        "categories": list_categories(db),
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "Shaastra Chatbot API"}
