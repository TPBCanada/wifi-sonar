from __future__ import annotations

import math
import random
import threading
import time
from collections import deque
from dataclasses import dataclass

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)


@dataclass(frozen=True)
class Anchor:
    id: str
    x: float
    y: float


ANCHORS = [
    Anchor("north-west", 0.35, 0.35),
    Anchor("north-east", 5.65, 0.35),
    Anchor("south-east", 5.65, 3.65),
    Anchor("south-west", 0.35, 3.65),
]
ROOM = {"width": 6.0, "height": 4.0, "name": "Demo room"}
measurements: dict[str, dict] = {}
trail = deque(maxlen=80)
lock = threading.Lock()
started = time.time()


def distance_from_rssi(rssi: float, tx_power: float = -48.0, path_loss: float = 2.35) -> float:
    """Log-distance path-loss estimate. Calibration is essential in real rooms."""
    return 10 ** ((tx_power - rssi) / (10 * path_loss))


def trilaterate(distances: dict[str, float]) -> tuple[float, float, float]:
    """Weighted nonlinear grid search; robust enough for an explainable MVP."""
    candidates = []
    for ix in range(61):
        x = ROOM["width"] * ix / 60
        for iy in range(41):
            y = ROOM["height"] * iy / 40
            error = 0.0
            weight = 0.0
            for anchor in ANCHORS:
                if anchor.id not in distances:
                    continue
                measured = max(0.05, distances[anchor.id])
                predicted = math.hypot(x - anchor.x, y - anchor.y)
                w = 1 / max(0.4, measured)
                error += w * (predicted - measured) ** 2
                weight += w
            if weight:
                candidates.append((error / weight, x, y))
    if not candidates:
        return ROOM["width"] / 2, ROOM["height"] / 2, 0.0
    error, x, y = min(candidates)
    confidence = max(0.05, min(0.99, math.exp(-error / 2)))
    return x, y, confidence


def simulated_readings() -> dict[str, dict]:
    t = time.time() - started
    x = 3 + 2.0 * math.sin(t / 5.2)
    y = 2 + 1.15 * math.cos(t / 3.7)
    moving = abs(math.sin(t * 1.7))
    result = {}
    for anchor in ANCHORS:
        d = max(0.25, math.hypot(x - anchor.x, y - anchor.y))
        rssi = -48 - 23.5 * math.log10(d) + random.gauss(0, 0.7)
        result[anchor.id] = {
            "rssi": round(rssi, 2),
            "distance": round(distance_from_rssi(rssi), 2),
            "motion": round(max(0, min(1, moving + random.gauss(0, 0.05))), 3),
            "updated": time.time(),
        }
    return result


def current_state() -> dict:
    with lock:
        recent = {k: v for k, v in measurements.items() if time.time() - v["updated"] < 5}
    source = recent if len(recent) >= 3 else simulated_readings()
    distances = {key: value["distance"] for key, value in source.items()}
    x, y, confidence = trilaterate(distances)
    motion = sum(v.get("motion", 0) for v in source.values()) / len(source)
    trail.append({"x": x, "y": y})
    return {
        "room": ROOM,
        "anchors": [a.__dict__ | source.get(a.id, {}) for a in ANCHORS],
        "target": {"x": x, "y": y, "confidence": confidence},
        "motion": motion,
        "presence": motion > 0.22,
        "trail": list(trail),
        "mode": "sensors" if len(recent) >= 3 else "simulation",
        "timestamp": time.time(),
    }


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/state")
def state():
    return jsonify(current_state())


@app.post("/api/readings")
def ingest():
    payload = request.get_json(force=True)
    anchor_id = payload.get("anchor_id")
    if anchor_id not in {a.id for a in ANCHORS}:
        return jsonify(error="unknown anchor_id"), 400
    try:
        rssi = float(payload["rssi"])
        motion = float(payload.get("motion", 0))
        distance = float(payload.get("distance", distance_from_rssi(rssi)))
    except (KeyError, TypeError, ValueError):
        return jsonify(error="rssi, distance, and motion must be numeric"), 400
    with lock:
        measurements[anchor_id] = {
            "rssi": rssi,
            "distance": max(0.05, distance),
            "motion": max(0, min(1, motion)),
            "updated": time.time(),
        }
    return jsonify(ok=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)

