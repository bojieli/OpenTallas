#!/usr/bin/env python3
"""DIE-S81-42 10-31 (COORD 06:45, AUTOBUILD-PIPE-5 NOTE): one-block tap splits for the types that plan_geom clock_tap_sinks
newly FAILs under the ring_read spread (10ea6e5e1).  delta_alltap_1030 machinery unchanged, except that a type ALREADY
grid+explicit keeps its added_taps and new ones are appended.  Taps only: nothing moves.
usage (repo root): delta_tapsplit_1031.py PLAN_IN PLAN_OUT REPORT.json --types REGEX"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import delta_alltap_1030 as D  # noqa: E402

_freeze = D.freeze


def freeze(P, raw, tn):
    ck = raw["partition_types"][tn]["clock"]
    if ck.get("tap_mode") == "grid+explicit":
        ck.setdefault("added_taps", [])
        return True
    return _freeze(P, raw, tn)


D.freeze = freeze
D.main()
