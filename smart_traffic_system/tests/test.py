"""
Day 1 Test — Verify environment is set up correctly.
Run: python tests/test_day1.py
"""

import sys

def check_import(name, package=None):
    pkg = package or name
    try:
        __import__(pkg)
        print(f"  [OK]  {name}")
        return True
    except ImportError:
        print(f"  [MISSING]  {name}  -->  pip install {pkg}")
        return False

print("\n=== Smart Traffic System — Day 1 Environment Check ===\n")

all_ok = True
all_ok &= check_import("OpenCV",       "cv2")
all_ok &= check_import("Ultralytics",  "ultralytics")
all_ok &= check_import("FastAPI",      "fastapi")
all_ok &= check_import("Uvicorn",      "uvicorn")
all_ok &= check_import("SQLAlchemy",   "sqlalchemy")
all_ok &= check_import("Requests",     "requests")

print()
if all_ok:
    print("All dependencies installed! Testing YOLOv8 model download...\n")
    try:
        from ultralytics import YOLO
        model = YOLO("yolov8n.pt")   # downloads ~6 MB automatically
        print("  [OK]  YOLOv8n model ready")
        print(f"  Model location: {model.ckpt_path}\n")
    except Exception as e:
        print(f"  [ERROR] YOLOv8 model load failed: {e}\n")
        all_ok = False

    print("Testing OpenCV video reading...\n")
    import cv2
    cap = cv2.VideoCapture(0)          # 0 = webcam; change to "data/traffic.mp4" for a file
    if cap.isOpened():
        ret, frame = cap.read()
        cap.release()
        if ret:
            print(f"  [OK]  Camera/video opened — frame shape: {frame.shape}\n")
        else:
            print("  [WARN]  Camera opened but no frame read. Use a video file instead.\n")
    else:
        print("  [WARN]  No webcam found. Place a traffic video at data/traffic.mp4\n")
        print("          Download one free from: https://www.pexels.com/search/videos/traffic/\n")
else:
    print("Fix the missing packages above, then re-run this script.\n")

print("=== Day 1 complete — move on to Day 2 ===\n" if all_ok else "=== Fix issues above first ===\n")

