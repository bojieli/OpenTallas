#!/usr/bin/env python3
"""DIE-QC-70 11-04: drop R8 pad-count straps the plan still declares and the bound RTL no longer has (cbf_q11 a4 PORT_BIND
bad_straps, 8 bits missing). Bind makes a strap only where the count differs across a type's instances, so an event that
evens a count drops the port; bound_r8_straps.project adds new rows at gen and never removes old ones. Authority = the bind
manifest. usage (repo root): delta_r8_stale.py PLAN BIND_OUT"""
import json
import sys
from pathlib import Path

P, B = sys.argv[1], Path(sys.argv[2])
t = Path(P).read_text()
p = json.loads(t)
sp = next(s for s in ((", ", ": "), (",", ":")) if json.dumps(p, separators=s) + "\n" == t)
m = json.loads((B / "bind_parent_id_straps.json").read_text())["types"]
for tn, v in p["partition_types"].items():
    if not isinstance(v, dict) or not v.get("count_straps") or tn not in m:
        continue
    bound = {k for k, x in m[tn].items() if x.get("kind") == "r8pad_strap"}
    keep = [c for c in v["count_straps"] if not c["name"].startswith("strap_r8pad_") or c["name"] in bound]
    gone = [c["name"] for c in v["count_straps"] if c not in keep]
    if gone:
        v["count_straps"] = keep
        print(tn, gone)
Path(P).write_text(json.dumps(p, separators=sp) + "\n")
