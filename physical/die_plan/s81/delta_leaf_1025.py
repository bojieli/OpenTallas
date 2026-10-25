#!/usr/bin/env python3
"""S81/LEAF4 10-25 leaf structural re-plan delta (in place on physical/die_plan/s81/die_plan.json).

Edits ONLY the 72 ot_s81sl_leaf types' hard_cores / internal_stations / ft_slots (payload delta_leaf_1025.json.gz,
built by cores/leaf/leaf4_payload.py from cores/leaf/corridor.py r3 + tools/die_plan/ft_sites.py) and re-prices the
die latency-table lanes whose leaf ft station count changed (cycles / stations / natural += planned - table; the lane
list and amounts are in the payload's 'latency' map, computed by G0 on the delta).  Fails closed when a leaf type's
other fields or a lane's current table value differ from what the delta was built on.
usage: delta_leaf_1025.py [PLAN_JSON]"""
import gzip
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
plan = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "die_plan.json"
D = json.load(gzip.open(HERE / "delta_leaf_1025.json.gz", "rt"))
P = json.load(open(plan))
for tn, upd in D["types"].items():
    T = P["partition_types"][tn]
    assert len(T["ft_slots"]) == len(upd["ft_slots"]), tn
    for s, n in zip(T["ft_slots"], upd["ft_slots"]):
        assert s["name"] == n["name"] and s["width"] == n["width"] and s["in_window_um"] == n["in_window_um"] \
            and s["out_window_um"] == n["out_window_um"], (tn, s["name"])
    assert {c["inst"] for c in T["hard_cores"]} == {c["inst"] for c in upd["hard_cores"]}, tn
    T.update(upd)
for ln, (old, new) in D.get("latency", {}).items():
    e = P["latency"]["lanes"][ln]
    assert e["cycles"] == old, (ln, e["cycles"], old)
    for k in ("cycles", "stations", "natural"):
        e[k] += new - old
plan.write_text(json.dumps(P, indent=0) + "\n")
print("leaf delta: %d types, %d lanes re-priced (net %+d cycles)" % (
    len(D["types"]), len(D.get("latency", {})), sum(n - o for o, n in D.get("latency", {}).values())))
