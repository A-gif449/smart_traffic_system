"""
config.py — Central configuration for Smart Traffic System
All other modules import settings from here.
"""

# ── Video source ──────────────────────────────────────────────────────────────
# Use 0 for webcam, or a file path like "data/traffic.mp4"
VIDEO_SOURCE = "data/traffic.mp4"

# ── YOLOv8 model ─────────────────────────────────────────────────────────────
MODEL_PATH = "yolov8n.pt"          # nano model — fast, good enough for counting

# COCO class IDs we care about
VEHICLE_CLASSES = {
    2:  "car",
    3:  "motorcycle",
    5:  "bus",
    7:  "truck",
}

DETECTION_CONFIDENCE = 0.4         # minimum confidence to count a detection

# ── Signal timing (seconds) ───────────────────────────────────────────────────
MIN_GREEN  = 10
MAX_GREEN  = 90
DEFAULT_GREEN = 30
YELLOW_TIME   = 3
ALL_RED_TIME  = 2

# Thresholds for adapting green time
HIGH_TRAFFIC  = 15                 # vehicles: extend green
LOW_TRAFFIC   = 4                  # vehicles: shorten green

# ── Intersection layout ───────────────────────────────────────────────────────
PHASES = ["North", "South", "East", "West"]

# ── Database ──────────────────────────────────────────────────────────────────
DB_PATH = "data/traffic.db"

# ── Backend API ───────────────────────────────────────────────────────────────
API_HOST = "127.0.0.1"
API_PORT = 8000

# ── Alerts ───────────────────────────────────────────────────────────────────
CONGESTION_CYCLES   = 3            # cycles above HIGH_TRAFFIC before alert
INCIDENT_DROP_RATIO = 0.3          # sudden drop below 30% of previous = incident