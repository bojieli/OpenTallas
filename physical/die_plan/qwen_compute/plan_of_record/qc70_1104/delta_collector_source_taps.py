#!/usr/bin/env python3
"""DIE-QC-70 11-04: added_tap_recentre republish re-solved coll_ft__cl78c7b300 to 4 taps and wrote the new tap index of its
collector sources into the sidecar only.  The plan kept tap 4 / 5, so landing_place found no rst_n_t4 and GEN + plan GEOM
stopped (StopIteration).  Copy the sidecar's index to the plan; RTL already follows the sidecar.  Idempotent; no other
field changes.  usage: delta_collector_source_taps.py PLAN SIDECAR"""
import json
import sys

path, sidecar = sys.argv[1:3]
text = open(path).read()
plan = json.loads(text)
seps = next(sp for sp in ((", ", ": "), (",", ":")) if json.dumps(plan, separators=sp) + "\n" == text)
side = json.load(open(sidecar))["collector"]["types"]
moved = []
for tn, st in sorted(side.items()):
    lc = plan["partition_types"].get(tn, {}).get("clock", {}).get("landing_contract", {})
    by = {s["name"]: s for s in st.get("local_sources", [])}
    for s in lc.get("collector_local_sources", []):
        new = by[s["name"]]["tap"]
        if s.get("tap") != new:
            moved.append((tn, s["name"], s.get("tap"), new))
            s["tap"] = new
open(path, "w").write(json.dumps(plan, separators=seps) + "\n")
print(len(moved), "moved", moved)
