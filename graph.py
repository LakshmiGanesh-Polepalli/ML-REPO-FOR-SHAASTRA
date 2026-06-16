"""
graph.py — IITM campus graph with Dijkstra pathfinding.
Nodes: named campus locations with approximate lat/lng and SVG coordinates.
Edges: walkable paths with distances in metres.
"""

import networkx as nx
import math
from typing import Optional

# ---------------------------------------------------------------------------
# Node definitions
# Each node: name -> {lat, lng, svg_x, svg_y, display_name}
# SVG canvas is 700 x 460 px (see frontend map)
# ---------------------------------------------------------------------------
NODES = {
    "Main Gate": {
        "lat": 12.9923, "lng": 80.2337,
        "svg_x": 320, "svg_y": 45,
        "display": "Main Gate",
        "desc": "Main entrance to IIT Madras campus"
    },
    "CLT": {
        "lat": 12.9908, "lng": 80.2340,
        "svg_x": 310, "svg_y": 155,
        "display": "CLT (Central Lecture Theatre)",
        "desc": "Central Lecture Theatre — primary academic hub"
    },
    "OAT": {
        "lat": 12.9898, "lng": 80.2318,
        "svg_x": 175, "svg_y": 215,
        "display": "OAT (Open Air Theatre)",
        "desc": "Open Air Theatre — main event venue"
    },
    "SAC": {
        "lat": 12.9915, "lng": 80.2362,
        "svg_x": 455, "svg_y": 185,
        "display": "SAC (Student Activity Centre)",
        "desc": "Student Activity Centre — sports & cultural hub"
    },
    "Himalaya": {
        "lat": 12.9885, "lng": 80.2308,
        "svg_x": 120, "svg_y": 300,
        "display": "Himalaya Hostel",
        "desc": "Himalaya Hostel — northern hostel zone"
    },
    "Godavari": {
        "lat": 12.9900, "lng": 80.2375,
        "svg_x": 520, "svg_y": 275,
        "display": "Godavari Hostel",
        "desc": "Godavari Hostel — eastern hostel zone"
    },
    "Jamuna": {
        "lat": 12.9920, "lng": 80.2385,
        "svg_x": 570, "svg_y": 180,
        "display": "Jamuna Hostel",
        "desc": "Jamuna Hostel — northeastern hostel zone"
    },
    "Sharavati": {
        "lat": 12.9872, "lng": 80.2325,
        "svg_x": 190, "svg_y": 380,
        "display": "Sharavati Hostel",
        "desc": "Sharavati Hostel — southern hostel zone"
    },
    "Taramani Gate": {
        "lat": 12.9865, "lng": 80.2378,
        "svg_x": 510, "svg_y": 400,
        "display": "Taramani Gate",
        "desc": "Taramani Gate — southern campus exit"
    },
}

# ---------------------------------------------------------------------------
# Edge definitions: (node_a, node_b, distance_metres)
# ---------------------------------------------------------------------------
EDGES = [
    ("Main Gate",   "CLT",          420),
    ("Main Gate",   "SAC",          600),
    ("Main Gate",   "Jamuna",       650),
    ("CLT",         "OAT",          380),
    ("CLT",         "SAC",          320),
    ("CLT",         "Himalaya",     430),
    ("OAT",         "SAC",          500),
    ("OAT",         "Himalaya",     280),
    ("OAT",         "Sharavati",    350),
    ("SAC",         "Godavari",     330),
    ("SAC",         "Jamuna",       240),
    ("Himalaya",    "Sharavati",    260),
    ("Godavari",    "Jamuna",       310),
    ("Godavari",    "Taramani Gate",360),
    ("Sharavati",   "Taramani Gate",430),
]

# ---------------------------------------------------------------------------
# Build graph
# ---------------------------------------------------------------------------
G = nx.Graph()
for name, data in NODES.items():
    G.add_node(name, **data)
for a, b, dist in EDGES:
    G.add_edge(a, b, weight=dist)


# ---------------------------------------------------------------------------
# Geolocation → nearest node
# ---------------------------------------------------------------------------
def _haversine(lat1, lng1, lat2, lng2) -> float:
    """Approximate distance in metres between two lat/lng points."""
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def nearest_node(lat: float, lng: float) -> str:
    best, best_d = None, float("inf")
    for name, data in NODES.items():
        d = _haversine(lat, lng, data["lat"], data["lng"])
        if d < best_d:
            best_d, best = d, name
    return best


# ---------------------------------------------------------------------------
# Dijkstra + turn-by-turn directions
# ---------------------------------------------------------------------------
def _cardinal(a_name: str, b_name: str) -> str:
    """Very rough compass direction from node a to node b (based on SVG coords)."""
    a, b = NODES[a_name], NODES[b_name]
    dx = b["svg_x"] - a["svg_x"]
    dy = b["svg_y"] - a["svg_y"]   # SVG y increases downward → south
    if abs(dx) > abs(dy) * 1.5:
        return "east" if dx > 0 else "west"
    if abs(dy) > abs(dx) * 1.5:
        return "south" if dy > 0 else "north"
    if dx > 0 and dy > 0: return "southeast"
    if dx > 0 and dy < 0: return "northeast"
    if dx < 0 and dy > 0: return "southwest"
    return "northwest"


def find_path(origin: str, destination: str) -> dict:
    """
    Returns dict with keys:
      path        — list of node names
      directions  — list of instruction strings
      total_dist  — int metres
      svg_coords  — list of {x, y} for frontend SVG
      error       — str or None
    """
    if origin not in G or destination not in G:
        return {"error": f"Unknown location(s): {origin}, {destination}"}

    if origin == destination:
        node = NODES[origin]
        return {
            "path": [origin],
            "directions": [f"You are already at {node['display']}!"],
            "total_dist": 0,
            "svg_coords": [{"x": node["svg_x"], "y": node["svg_y"]}],
            "error": None,
        }

    try:
        path = nx.dijkstra_path(G, origin, destination, weight="weight")
        total = int(nx.dijkstra_path_length(G, origin, destination, weight="weight"))
    except nx.NetworkXNoPath:
        return {"error": f"No path found between {origin} and {destination}."}

    directions = []
    for i, node in enumerate(path):
        if i == 0:
            directions.append(
                f"🟢 Start at **{NODES[node]['display']}**."
            )
        elif i == len(path) - 1:
            dist = G[path[i - 1]][node]["weight"]
            direction = _cardinal(path[i - 1], node)
            directions.append(
                f"➡️  Head {direction} for ~{dist}m to reach **{NODES[node]['display']}**. "
                f"You have arrived! 🏁"
            )
        else:
            dist = G[path[i - 1]][node]["weight"]
            direction = _cardinal(path[i - 1], node)
            directions.append(
                f"➡️  Head {direction} for ~{dist}m to **{NODES[node]['display']}**."
            )

    svg_coords = [
        {"x": NODES[n]["svg_x"], "y": NODES[n]["svg_y"]} for n in path
    ]

    return {
        "path": path,
        "directions": directions,
        "total_dist": total,
        "svg_coords": svg_coords,
        "error": None,
    }


def get_node_info(name: str) -> Optional[dict]:
    return NODES.get(name)


def all_nodes_svg() -> list[dict]:
    """Return all node positions for the frontend to render the base map."""
    return [
        {
            "name": k,
            "display": v["display"],
            "x": v["svg_x"],
            "y": v["svg_y"],
        }
        for k, v in NODES.items()
    ]


def all_edges_svg() -> list[dict]:
    """Return all edges as SVG line data."""
    result = []
    for a, b, dist in EDGES:
        result.append({
            "x1": NODES[a]["svg_x"], "y1": NODES[a]["svg_y"],
            "x2": NODES[b]["svg_x"], "y2": NODES[b]["svg_y"],
            "dist": dist,
        })
    return result
