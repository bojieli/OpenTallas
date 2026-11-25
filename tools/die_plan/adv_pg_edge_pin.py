"""ADV-PG-EDGE-PIN: see adv_geom_static.py (COORD 11-24; WARN only, never a gate)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from adv_geom_static import pg_edge_pin as findings  # noqa: E402,F401
