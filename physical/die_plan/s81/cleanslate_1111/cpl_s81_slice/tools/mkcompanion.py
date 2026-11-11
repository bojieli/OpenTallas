#!/usr/bin/env python3
"""CPL-S81-SLICE: composer companion (DS85-COMPOSE-1111 --derived) from the lane's applied plan:
per delta type, core taps of the moved cores (rigid with their core) and every internal station's from/to/regs.
usage: mkcompanion.py LANE_PLAN DELTA OUT"""
import json
import sys

L, D = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
out = {}
for tn, m in sorted(D.items()):
    t = L["partition_types"][tn]
    hcs = sorted({h["inst"] for h in t["hard_cores"]}, key=len, reverse=True)

    def own(n):
        return next((i for i in hcs if n == i or n.startswith(i + ".")), None)
    taps = {tp["name"]: tp["xy"] for tp in (t.get("clock") or {}).get("taps", []) if tp.get("kind") == "core" and own(tp["name"]) in m}
    st = [{k: s[k] for k in ("from_um", "to_um", "regs_um") if k in s} for s in t.get("internal_stations") or []]
    out[tn] = {"core_taps": taps, "internal_stations": st}
json.dump(out, open(sys.argv[3], "w"), indent=1, sort_keys=True)
print({k: (len(v["core_taps"]), len(v["internal_stations"])) for k, v in out.items()})
