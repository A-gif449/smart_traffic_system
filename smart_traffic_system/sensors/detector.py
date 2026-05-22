"""
sensors/detector.py — Vehicle detection using YOLOv8
Day 2 core module. Reads video frames, detects and counts vehicles.

Run standalone to test:
    python sensors/detector.py
"""

import cv2
import time
import sys, os
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import (VIDEO_SOURCE, MODEL_PATH, VEHICLE_CLASSES,
                    DETECTION_CONFIDENCE, PHASES)

try:
    from ultralytics import YOLO
except ImportError:
    print("[ERROR] Run: pip install ultralytics")
    sys.exit(1)


class VehicleDetector:
    """
    Loads YOLOv8, reads frames from video source,
    returns per-frame vehicle counts and annotated frames.
    """

    def __init__(self, source=VIDEO_SOURCE, model_path=MODEL_PATH):
        print("[Detector] Loading YOLOv8 model...")
        self.model  = YOLO(model_path)
        self.source = source
        self.cap    = None
        self.current_counts = defaultdict(int)   # class_name → count this frame
        self.frame_number   = 0

    # ── video capture ────────────────────────────────────────────────────────

    def open(self):
        self.cap = cv2.VideoCapture(self.source)
        if not self.cap.isOpened():
            raise RuntimeError(
                f"Cannot open video source: {self.source}\n"
                "  → For webcam use source=0\n"
                "  → For file place video at data/traffic.mp4"
            )
        fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
        print(f"[Detector] Opened source: {self.source}  |  FPS: {fps:.1f}")
        return self

    def release(self):
        if self.cap:
            self.cap.release()

    # ── detection ────────────────────────────────────────────────────────────

    def read_frame(self):
        """Read one frame. Returns (success, frame)."""
        if not self.cap:
            self.open()
        ret, frame = self.cap.read()
        # Loop video file when it ends
        if not ret:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()
        return ret, frame

    def detect(self, frame):
        """
        Run YOLOv8 on frame.
        Returns:
            counts  dict  { 'car': 3, 'truck': 1, 'total': 4 }
            annotated_frame  ndarray  frame with bounding boxes drawn
        """
        results = self.model(frame, conf=DETECTION_CONFIDENCE,
                             classes=list(VEHICLE_CLASSES.keys()), verbose=False)

        counts = defaultdict(int)
        annotated = frame.copy()

        for result in results:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                cls_name = VEHICLE_CLASSES.get(cls_id, "vehicle")
                conf = float(box.conf[0])
                counts[cls_name] += 1

                # Draw bounding box
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                color = {
                    "car":        (56, 158, 29),   # green
                    "truck":      (208, 90, 48),    # orange
                    "bus":        (83, 104, 184),   # blue
                    "motorcycle": (184, 83, 148),   # purple
                }.get(cls_name, (200, 200, 200))

                cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
                label = f"{cls_name} {conf:.2f}"
                cv2.putText(annotated, label, (x1, y1 - 6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 1)

        counts["total"] = sum(counts[c] for c in ["car", "truck", "bus", "motorcycle"])
        self.current_counts = counts
        self.frame_number  += 1
        return dict(counts), annotated

    def annotate_overlay(self, frame, counts):
        """Draw a count overlay panel on the frame."""
        h, w = frame.shape[:2]
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (220, 130), (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)

        lines = [
            f"  Total  : {counts.get('total', 0)}",
            f"  Cars   : {counts.get('car', 0)}",
            f"  Trucks : {counts.get('truck', 0)}",
            f"  Buses  : {counts.get('bus', 0)}",
            f"  Bikes  : {counts.get('motorcycle', 0)}",
        ]
        for i, text in enumerate(lines):
            cv2.putText(frame, text, (8, 22 + i * 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (230, 230, 230), 1)
        return frame

    # ── convenience generator ────────────────────────────────────────────────

    def stream(self):
        """
        Generator: yields (counts, annotated_frame) for each frame.
        Usage:
            for counts, frame in detector.stream():
                ...
        """
        self.open()
        try:
            while True:
                ret, frame = self.read_frame()
                if not ret:
                    break
                counts, annotated = self.detect(frame)
                annotated = self.annotate_overlay(annotated, counts)
                yield counts, annotated
        finally:
            self.release()


# ── standalone test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=VIDEO_SOURCE,
                        help="Video path or 0 for webcam")
    parser.add_argument("--show", action="store_true",
                        help="Display annotated video window")
    args = parser.parse_args()

    detector = VehicleDetector(source=args.source)
    print("[Detector] Running — press Q to quit\n")

    prev_time = time.time()
    for counts, frame in detector.stream():
        now  = time.time()
        fps  = 1.0 / max(now - prev_time, 0.001)
        prev_time = now

        print(f"\r  Frame {detector.frame_number:5d} | "
              f"Total: {counts.get('total',0):3d} | "
              f"Cars: {counts.get('car',0):2d}  "
              f"Trucks: {counts.get('truck',0):2d}  "
              f"Buses: {counts.get('bus',0):2d}  "
              f"Bikes: {counts.get('motorcycle',0):2d}  "
              f"FPS: {fps:4.1f}", end="")

        if args.show:
            cv2.imshow("Smart Traffic — Vehicle Detection (Q to quit)", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cv2.destroyAllWindows()
    print("\n[Detector] Done.")