#!/usr/bin/env python3
"""DIE-HBM-23 post-fix 2 on the re-plan event output: a type clock tap (clock.tap_um, and clock.taps[].xy_um if any)
that falls outside a re-sized outline (filler spu0/spu1 widths changed by the event) moves to the outline centre
(the filler has no sinks of its own; reported).  usage: post_fix2.py PLAN_JSON"""
import json, sys
raw = json.load(open(sys.argv[1]))
fixed = []
for tn, t in raw["partition_types"].items():
    w, h = t["outline_um"]
    ck = t.get("clock") or {}
    xy = ck.get("tap_um")
    if xy and not (0 <= xy[0] <= w and 0 <= xy[1] <= h):
        ck["tap_um"] = [round(w / 2, 4), round(h / 2, 4)]
        fixed.append(dict(type=tn, old=xy, new=ck["tap_um"]))
    for tap in ck.get("taps", []):
        p = tap.get("xy_um")
        if p and not (0 <= p[0] <= w and 0 <= p[1] <= h):
            raise SystemExit(f"{tn}: sub-tap {tap.get(name)} outside outline - not handled")
json.dump(raw, open(sys.argv[1], "w"), indent=1)
print("clock taps moved", fixed)
