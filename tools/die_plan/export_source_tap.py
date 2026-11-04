#!/usr/bin/env python3
"""FWDCLK-1 11-04: plan delta, forwarded clock outputs taken from their nearest tap instead of root clk.

compose(forward_source="clk") (KV, QC) stores the nearest tap in source_clock_tap and leaves source_clock_port = clk, and
every reader (RTL assign, SDC -source, landing_exports.tcl) reads source_clock_port. The export then hangs on root clk at
the partition centre with a long wire to the port. This applies the form S81 and HEAD already use (DIE-HEAD-50 l48c):
source_clock_port = the tap, forwarded_clock_only_inputs = true, so all three readers follow and LEC stays consistent.
An export whose tap is clk, or whose tap the type no longer plans, is unchanged and reported.
usage: export_source_tap.py PLAN_IN PLAN_OUT"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schema as S  # noqa: E402


def apply(raw):
    """Edit raw in place -> {type: [[pin, old port, tap]]}, {type: [[pin, tap]]} for taps not planned."""
    P = S.Plan(raw)
    changed, missing = {}, {}
    for tn, t in raw["partition_types"].items():
        lc = (t.get("clock") or {}).get("landing_contract") or {}
        pins = [p for p in lc.get("pins", []) if p.get("kind") == "clock" and p.get("dir") == "out"]
        todo = [p for p in pins if p.get("source_clock_tap") not in (None, "clk", p.get("source_clock_port"))]
        if not todo:
            continue
        planned = {n for n, _x, _y in S.tap_grid(P, tn)}
        for p in todo:
            if p["source_clock_tap"] in planned:
                changed.setdefault(tn, []).append([p["name"], p["source_clock_port"], p["source_clock_tap"]])
                p["source_clock_port"] = p["source_clock_tap"]
            else:
                missing.setdefault(tn, []).append([p["name"], p["source_clock_tap"]])
        if tn in changed:
            lc["forwarded_clock_only_inputs"] = True
    return changed, missing


def main(argv):
    raw = json.loads(Path(argv[1]).read_text())
    changed, missing = apply(raw)
    Path(argv[2]).write_text(json.dumps(raw, indent=1) + "\n")
    print(f"{len(changed)} types, {sum(map(len, changed.values()))} exports changed; "
          f"{sum(map(len, missing.values()))} taps not planned {dict(list(missing.items())[:5])}")


if __name__ == "__main__":
    main(sys.argv)
