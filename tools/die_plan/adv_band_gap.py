"""ADV-BAND-GAP: see adv_geom_static.py (COORD flow review 11-22 item 2; WARN only, never a gate)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from adv_geom_static import band_gap as findings  # noqa: E402,F401
