"""ADV-CHANNEL-WIDTH: see adv_slot_gap.py (FP-CONVERGE-S81 11-25; WARN only, never a gate)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from adv_slot_gap import findings_channel as findings  # noqa: E402,F401
