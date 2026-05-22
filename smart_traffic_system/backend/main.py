"""
backend/main.py — FastAPI backend for Smart Traffic System
Day 4. Serves REST endpoints + WebSocket live updates.

Run:  uvicorn backend.main:app --reload --port 8000
"""

import asyncio
import json
import threading
import time
from datetime import datetime, timedelta
from collections import defaultdict, deque
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import PHASES, HIGH_TRAFFIC, CONGESTION_CYCLES, INCIDENT_DROP_RATIO
from sensors.signal_controller import SignalController
from models.database import init_db, SessionLocal, TrafficCount, SignalEvent, Alert

# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(title="Smart Traffic System API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # In production, restrict this
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Shared state ──────────────────────────────────────────────────────────────

controller  = SignalController()

# In-memory ring buffer: last 60 count records per phase
count_history: dict[str, deque] = {p: deque(maxlen=60) for p in PHASES}

# Track congestion for alert logic
congestion_streak: dict[str, int] = defaultdict(int)
last_counts:       dict[str, int] = defaultdict(int)

# Connected WebSocket clients
ws_clients: list[WebSocket] = []


# ── Lifecycle ─────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    init_db()
    controller.start()
    asyncio.create_task(ws_broadcast_loop())
    print("[API] Server started.")


@app.on_event("shutdown")
async def shutdown():
    controller.stop()


# ── REST endpoints ────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "Smart Traffic System API", "docs": "/docs"}


@app.get("/signal/state")
def get_signal_state():
    """Current signal phase for all directions."""
    return {
        "timestamp":    datetime.utcnow().isoformat(),
        "active_phase": controller.get_active_phase(),
        "phases":       controller.get_all_states(),
    }


@app.post("/signal/override/{phase}")
def override_signal(phase: str):
    """Manually jump to a specific phase."""
    if phase not in PHASES:
        raise HTTPException(status_code=400,
                            detail=f"Phase must be one of {PHASES}")
    controller.force_phase(phase)
    return {"message": f"Switched to phase: {phase}"}


@app.post("/traffic/update")
def update_traffic(data: dict):
    """
    Receive vehicle count from the detector.
    Body: { "phase": "North", "counts": {"car":3,"truck":1,"total":4} }
    """
    phase  = data.get("phase", "North")
    counts = data.get("counts", {})
    total  = counts.get("total", 0)

    controller.update_counts(phase, counts)

    # Save to history
    record = {
        "timestamp": datetime.utcnow().isoformat(),
        "phase":     phase,
        "total":     total,
        "car":       counts.get("car", 0),
        "truck":     counts.get("truck", 0),
        "bus":       counts.get("bus", 0),
        "motorcycle":counts.get("motorcycle", 0),
    }
    count_history[phase].append(record)

    # Alert logic
    _check_alerts(phase, total)

    # Persist to DB
    _save_count_to_db(phase, counts)

    return {"status": "ok", "phase": phase, "total": total}


@app.get("/traffic/count")
def get_current_counts():
    """Latest vehicle count from each phase."""
    result = {}
    for phase in PHASES:
        hist = count_history[phase]
        if hist:
            result[phase] = hist[-1]
        else:
            result[phase] = {"phase": phase, "total": 0}
    return result


@app.get("/traffic/history")
def get_history(phase: Optional[str] = None, minutes: int = 60):
    """Count history. Filter by phase and time window."""
    cutoff = datetime.utcnow() - timedelta(minutes=minutes)
    out = {}
    phases_to_check = [phase] if phase and phase in PHASES else PHASES
    for p in phases_to_check:
        out[p] = [
            r for r in count_history[p]
            if datetime.fromisoformat(r["timestamp"]) >= cutoff
        ]
    return out


@app.get("/alerts")
def get_alerts():
    """Recent open alerts."""
    db = SessionLocal()
    try:
        alerts = db.query(Alert).filter(Alert.resolved == 0)\
                   .order_by(Alert.timestamp.desc()).limit(20).all()
        return [
            {
                "id":         a.id,
                "type":       a.alert_type,
                "phase":      a.phase,
                "message":    a.message,
                "timestamp":  a.timestamp.isoformat(),
            }
            for a in alerts
        ]
    finally:
        db.close()


@app.post("/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: int):
    db = SessionLocal()
    try:
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        alert.resolved = 1
        db.commit()
        return {"message": "Alert resolved"}
    finally:
        db.close()


@app.get("/signal/events")
def get_signal_events():
    """Recent signal phase change log."""
    return controller.get_event_log(limit=30)


# ── WebSocket ─────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    ws_clients.append(ws)
    try:
        while True:
            await ws.receive_text()   # keep connection alive
    except WebSocketDisconnect:
        ws_clients.remove(ws)


async def ws_broadcast_loop():
    """Push live state to all connected dashboard clients every second."""
    while True:
        await asyncio.sleep(1)
        if not ws_clients:
            continue
        payload = json.dumps({
            "type":         "state_update",
            "timestamp":    datetime.utcnow().isoformat(),
            "active_phase": controller.get_active_phase(),
            "phases":       controller.get_all_states(),
            "counts":       {
                p: (count_history[p][-1] if count_history[p] else {"total": 0})
                for p in PHASES
            },
        })
        dead = []
        for ws in ws_clients:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            ws_clients.remove(ws)


# ── Alert logic ───────────────────────────────────────────────────────────────

def _check_alerts(phase: str, total: int):
    # Congestion check
    if total >= HIGH_TRAFFIC:
        congestion_streak[phase] += 1
        if congestion_streak[phase] == CONGESTION_CYCLES:
            _save_alert("CONGESTION", phase,
                        f"High traffic on {phase}: {total} vehicles for "
                        f"{CONGESTION_CYCLES} consecutive cycles.")
    else:
        congestion_streak[phase] = 0

    # Incident: sudden drop after congestion
    prev = last_counts[phase]
    if prev >= HIGH_TRAFFIC and total < prev * INCIDENT_DROP_RATIO:
        _save_alert("INCIDENT", phase,
                    f"Possible incident on {phase}: count dropped from "
                    f"{prev} to {total} vehicles suddenly.")
    last_counts[phase] = total


def _save_alert(alert_type: str, phase: str, message: str):
    print(f"[ALERT] {alert_type} — {phase}: {message}")
    db = SessionLocal()
    try:
        db.add(Alert(alert_type=alert_type, phase=phase, message=message))
        db.commit()
    finally:
        db.close()


def _save_count_to_db(phase: str, counts: dict):
    db = SessionLocal()
    try:
        db.add(TrafficCount(
            phase=phase,
            car_count=counts.get("car", 0),
            truck_count=counts.get("truck", 0),
            bus_count=counts.get("bus", 0),
            bike_count=counts.get("motorcycle", 0),
            total=counts.get("total", 0),
        ))
        db.commit()
    finally:
        db.close()