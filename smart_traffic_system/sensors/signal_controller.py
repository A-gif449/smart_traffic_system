"""
sensors/signal_controller.py — Adaptive traffic signal timing engine
Day 3 core module. Computes optimal green time using vehicle counts.

Run standalone to simulate:
    python sensors/signal_controller.py
"""

import time
import threading
import sys, os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import (PHASES, MIN_GREEN, MAX_GREEN, DEFAULT_GREEN,
                    YELLOW_TIME, ALL_RED_TIME, HIGH_TRAFFIC, LOW_TRAFFIC)


# ── Signal state ──────────────────────────────────────────────────────────────

class SignalState:
    GREEN    = "GREEN"
    YELLOW   = "YELLOW"
    RED      = "RED"
    ALL_RED  = "ALL_RED"


class PhaseController:
    """
    Manages one intersection phase (e.g. North).
    Tracks current state, time remaining, and counts.
    """

    def __init__(self, name):
        self.name          = name
        self.state         = SignalState.RED
        self.time_left     = 0.0
        self.vehicle_count = 0
        self.green_duration = DEFAULT_GREEN

    def to_dict(self):
        return {
            "phase":         self.name,
            "state":         self.state,
            "time_left":     round(self.time_left, 1),
            "vehicle_count": self.vehicle_count,
            "green_duration": self.green_duration,
        }


# ── Webster adaptive timing ───────────────────────────────────────────────────

def webster_green_time(vehicle_count: int) -> float:
    """
    Simplified Webster formula:
    Base green time scaled linearly by vehicle density.
    Clamped to [MIN_GREEN, MAX_GREEN].
    """
    if vehicle_count >= HIGH_TRAFFIC:
        # Scale up toward MAX_GREEN
        ratio = min((vehicle_count - HIGH_TRAFFIC) / 20.0, 1.0)
        return round(DEFAULT_GREEN + ratio * (MAX_GREEN - DEFAULT_GREEN), 1)
    elif vehicle_count <= LOW_TRAFFIC:
        # Scale down toward MIN_GREEN
        ratio = vehicle_count / max(LOW_TRAFFIC, 1)
        return round(MIN_GREEN + ratio * (DEFAULT_GREEN - MIN_GREEN), 1)
    else:
        # Linear interpolation between LOW and HIGH thresholds
        ratio = (vehicle_count - LOW_TRAFFIC) / max(HIGH_TRAFFIC - LOW_TRAFFIC, 1)
        return round(MIN_GREEN + ratio * (DEFAULT_GREEN - MIN_GREEN), 1)


# ── Signal controller ─────────────────────────────────────────────────────────

class SignalController:
    """
    4-phase adaptive signal controller.

    Cycle: GREEN(phase N) → YELLOW(phase N) → ALL_RED → GREEN(phase N+1) → …

    Call update_counts() to feed new vehicle data.
    Call get_all_states() to read current phase states.
    """

    def __init__(self):
        self.phases     = {name: PhaseController(name) for name in PHASES}
        self.phase_list = PHASES                      # cycle order
        self.current_idx  = 0
        self.active_phase = self.phase_list[0]
        self._lock        = threading.Lock()
        self._running     = False
        self._thread      = None
        self._event_log   = []                        # list of dicts for API

    # ── public API ────────────────────────────────────────────────────────────

    def update_counts(self, phase_name: str, counts: dict):
        """Feed new vehicle count data for a phase."""
        with self._lock:
            if phase_name in self.phases:
                self.phases[phase_name].vehicle_count = counts.get("total", 0)

    def get_all_states(self) -> list:
        with self._lock:
            return [p.to_dict() for p in self.phases.values()]

    def get_active_phase(self) -> str:
        return self.active_phase

    def force_phase(self, phase_name: str):
        """Manual override — jump to a specific phase immediately."""
        with self._lock:
            if phase_name in self.phases:
                self.current_idx  = self.phase_list.index(phase_name)
                self.active_phase = phase_name
                print(f"[Signal] Manual override → {phase_name}")

    def get_event_log(self, limit=50) -> list:
        return self._event_log[-limit:]

    # ── internal cycle loop ───────────────────────────────────────────────────

    def _run_cycle(self):
        """
        Main loop: runs each phase through GREEN → YELLOW → ALL_RED.
        Adapts green duration from latest vehicle count.
        """
        while self._running:
            with self._lock:
                idx   = self.current_idx
                name  = self.phase_list[idx]
                phase = self.phases[name]
                count = phase.vehicle_count
                green_t = webster_green_time(count)
                phase.green_duration = green_t
                self.active_phase = name
                # All others RED
                for n, p in self.phases.items():
                    p.state     = SignalState.RED
                    p.time_left = green_t + YELLOW_TIME + ALL_RED_TIME
                phase.state     = SignalState.GREEN
                phase.time_left = green_t

            self._log_event(name, SignalState.GREEN, green_t)
            self._countdown(phase, green_t, SignalState.GREEN)

            # YELLOW
            with self._lock:
                phase.state     = SignalState.YELLOW
                phase.time_left = YELLOW_TIME
            self._log_event(name, SignalState.YELLOW, YELLOW_TIME)
            self._countdown(phase, YELLOW_TIME, SignalState.YELLOW)

            # ALL RED
            with self._lock:
                for p in self.phases.values():
                    p.state     = SignalState.ALL_RED
                    p.time_left = ALL_RED_TIME
            self._log_event(name, SignalState.ALL_RED, ALL_RED_TIME)
            time.sleep(ALL_RED_TIME)

            # Advance to next phase
            with self._lock:
                self.current_idx = (self.current_idx + 1) % len(self.phase_list)

    def _countdown(self, phase, duration, state):
        """Sleep duration seconds, decrementing time_left each second."""
        steps = int(duration)
        for i in range(steps):
            if not self._running:
                return
            time.sleep(1.0)
            with self._lock:
                phase.time_left = max(0, duration - i - 1)
        # sleep remainder
        frac = duration - steps
        if frac > 0 and self._running:
            time.sleep(frac)

    def _log_event(self, phase, state, duration):
        self._event_log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "phase":     phase,
            "state":     state,
            "duration":  duration,
        })
        # Keep only last 200 events
        if len(self._event_log) > 200:
            self._event_log = self._event_log[-200:]

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def start(self):
        self._running = True
        self._thread  = threading.Thread(target=self._run_cycle, daemon=True)
        self._thread.start()
        print("[Signal] Controller started.")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        print("[Signal] Controller stopped.")


# ── standalone simulation ─────────────────────────────────────────────────────

if __name__ == "__main__":
    import random

    controller = SignalController()
    controller.start()

    print("\n=== Signal Controller Simulation ===")
    print("Feeding random vehicle counts. Ctrl+C to stop.\n")

    try:
        cycle = 0
        while True:
            # Simulate varying traffic on each phase
            for phase in PHASES:
                fake_count = random.randint(0, 30)
                controller.update_counts(phase, {"total": fake_count})

            # Print all phase states
            states = controller.get_all_states()
            print(f"\n--- Cycle {cycle} ---")
            for s in states:
                bar = "●" if s["state"] == "GREEN" else ("○" if s["state"] == "YELLOW" else " ")
                print(f"  {bar} {s['phase']:6s}  {s['state']:8s}  "
                      f"{s['time_left']:5.1f}s left  "
                      f"count={s['vehicle_count']:2d}  "
                      f"green={s['green_duration']}s  "
                      f"[Webster: {webster_green_time(s['vehicle_count'])}s]")
            cycle += 1
            time.sleep(2)

    except KeyboardInterrupt:
        controller.stop()
        print("\nSimulation ended.")