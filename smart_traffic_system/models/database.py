"""
models/database.py — SQLite database setup using SQLAlchemy
Run standalone to create the DB: python models/database.py
"""

import sys, os

# Fix path — works whether run from project root OR from models/ folder OR via VS Code debugger
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

# Now config.py will always be found
from config import DB_PATH

DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


# ── Table: vehicle counts recorded each detection cycle ──────────────────────
class TrafficCount(Base):
    __tablename__ = "traffic_counts"

    id          = Column(Integer, primary_key=True, index=True)
    timestamp   = Column(DateTime, default=datetime.utcnow)
    phase       = Column(String(20))        # North / South / East / West
    car_count   = Column(Integer, default=0)
    truck_count = Column(Integer, default=0)
    bus_count   = Column(Integer, default=0)
    bike_count  = Column(Integer, default=0)
    total       = Column(Integer, default=0)


# ── Table: signal phase change log ───────────────────────────────────────────
class SignalEvent(Base):
    __tablename__ = "signal_events"

    id        = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    phase     = Column(String(20))
    state     = Column(String(10))          # GREEN / YELLOW / RED / ALL_RED
    duration  = Column(Float)               # seconds this state was active


# ── Table: alerts and incidents ───────────────────────────────────────────────
class Alert(Base):
    __tablename__ = "alerts"

    id         = Column(Integer, primary_key=True, index=True)
    timestamp  = Column(DateTime, default=datetime.utcnow)
    alert_type = Column(String(30))         # CONGESTION / INCIDENT / INFO
    phase      = Column(String(20))
    message    = Column(Text)
    resolved   = Column(Integer, default=0) # 0 = open, 1 = resolved


def init_db():
    """Create all tables if they don't exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    Base.metadata.create_all(bind=engine)
    print(f"[DB] Database ready at {DB_PATH}")


def get_db():
    """Dependency for FastAPI routes — yields a session then closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    print(f"[DB] Project root: {_project_root}")
    print(f"[DB] DB path:      {DB_PATH}")
    init_db()
    print("[DB] All tables created successfully.")