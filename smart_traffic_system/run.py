"""
run.py — Start the full Smart Traffic System in one command.

What this does:
  1. Starts the FastAPI backend server (background thread)
  2. Opens the video source and runs YOLOv8 detection
  3. Sends each frame's counts to the backend API
  4. Optionally shows an annotated video window

Usage:
    python run.py                        # uses config.py defaults
    python run.py --source 0             # webcam
    python run.py --source data/traffic.mp4 --show
    python run.py --simulate             # no video, random counts (demo mode)
"""

import argparse
import threading
import time
import requests
import random
import sys

from config import VIDEO_SOURCE, API_HOST, API_PORT, PHASES

API_BASE = f"http://{API_HOST}:{API_PORT}"


# ── Start backend in background thread ───────────────────────────────────────

def start_backend():
    import uvicorn
    uvicorn.run("backend.main:app",
                host=API_HOST, port=API_PORT,
                log_level="warning", reload=False)


# ── Send counts to API ────────────────────────────────────────────────────────

def post_counts(phase: str, counts: dict):
    try:
        requests.post(f"{API_BASE}/traffic/update",
                      json={"phase": phase, "counts": counts},
                      timeout=60.0)
    except requests.exceptions.ConnectionError:
        pass   # backend not yet ready — skip


# ── Simulation mode (no video needed) ────────────────────────────────────────

def run_simulation():
    print("[Runner] Simulation mode — sending random vehicle counts to API")
    tick = 0
    while True:
        for phase in PHASES:
            # Simulate rush-hour pattern: counts spike every 30 ticks
            base = 5 + (20 if (tick % 30 < 10) else 0)
            counts = {
                "car":        random.randint(base, base + 8),
                "truck":      random.randint(0, 3),
                "bus":        random.randint(0, 2),
                "motorcycle": random.randint(0, 4),
            }
            counts["total"] = sum(counts[k] for k in ["car","truck","bus","motorcycle"])
            post_counts(phase, counts)
            print(f"\r  tick {tick:4d} | {phase:6s} total={counts['total']:2d} ", end="")
        tick += 1
        time.sleep(2)


# ── Real detector mode ────────────────────────────────────────────────────────

def run_detector(source, show=False):
    import cv2
    from sensors.detector import VehicleDetector

    detector = VehicleDetector(source=source)
    print(f"[Runner] Detection mode — source: {source}")

    # Cycle through phases to simulate per-direction counts
    # In a real deployment each direction has its own camera
    phase_idx = 0

    for counts, frame in detector.stream():
        phase = PHASES[phase_idx % len(PHASES)]
        post_counts(phase, counts)
        phase_idx += 1

        if show:
            cv2.imshow("Smart Traffic System (Q to quit)", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cv2.destroyAllWindows()


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Smart Traffic System Runner")
    parser.add_argument("--source",   default=VIDEO_SOURCE,
                        help="Video file path or 0 for webcam")
    parser.add_argument("--show",     action="store_true",
                        help="Show annotated video window")
    parser.add_argument("--simulate", action="store_true",
                        help="Use random counts instead of real video")
    args = parser.parse_args()

    print("\n=== Smart Traffic System ===")
    print(f"  API:  {API_BASE}")
    print(f"  Mode: {'simulation' if args.simulate else f'detection ({args.source})'}\n")

    # Start backend in background
    backend_thread = threading.Thread(target=start_backend, daemon=True)
    backend_thread.start()

    # Wait for backend to be ready
    print("[Runner] Waiting for API to start", end="", flush=True)
    for _ in range(20):
        try:
            requests.get(f"{API_BASE}/", timeout=1)
            break
        except Exception:
            print(".", end="", flush=True)
            time.sleep(0.5)
    print(" ready!\n")

    print(f"[Runner] Dashboard: open dashboard/index.html in a browser")
    print(f"[Runner] API docs:  {API_BASE}/docs\n")

    if args.simulate:
        run_simulation()
    else:
        run_detector(args.source, show=args.show)


if __name__ == "__main__":
    main()