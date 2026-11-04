#!/usr/bin/env python3
"""Write a copy of a frozen plan pinned to the clock-tap and reset-relay models it was solved with.

A plan's reset_start_raw_exports, landing raw_reset names and collector snapshots name relays by the solved graph
(u_rrl_<k>).  Main re-solves taps since 0ddc1ccd8c8/e2a63cfee7d and relays since 74080dbb823, so such a plan stops
matching it.  This sets, on every type, clock.tap_model = "frozen_anchor" and reset.obstacle_model = "lef_origin".
Metadata only: no geometry, pin or net in the plan changes.

    python3 tools/die_plan/pin_frozen_tap_model.py IN_PLAN.json OUT_PLAN.json
"""
import json
import sys
from pathlib import Path


def pin(raw):
    for t in raw["partition_types"].values():
        t.setdefault("clock", {})["tap_model"] = "frozen_anchor"
        t.setdefault("reset", {})["obstacle_model"] = "lef_origin"
    return raw


def main(argv):
    if len(argv) != 3:
        raise SystemExit(__doc__)
    src, dst = Path(argv[1]), Path(argv[2])
    if dst.exists() and dst.resolve() == src.resolve():
        raise SystemExit("refusing to pin a plan in place: OUT must be a new file")
    dst.write_text(json.dumps(pin(json.loads(src.read_text())), indent=1) + "\n")


if __name__ == "__main__":
    main(sys.argv)
