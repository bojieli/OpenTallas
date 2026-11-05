#!/usr/bin/env python3
"""DIE-QC-71 11-04: plan landing_contract.collector_children[].node := the sidecar's re-noded child.

renode_collector.py --write (DIE-QC-68) re-derived the nodes in the sidecar only. bind emits RTL from the sidecar, gen's
landing_placement.tcl (landing_place.tcl) reads the plan contract: a stale child names a collector the RTL does not have,
and global place stops: OT_CLAND no mapped cells found under u_cland_collect_rst_n_t10 (sle_hc1__cl7d360508 a4 22:21,
cbx_q10__cl89936551 17:16). RTL does not change. Only the node field of a mismatched child changes; xy_um must already agree.

    sync_contract_collector_nodes.py PLAN SIDECAR [OUT]   (default OUT = PLAN)
"""
import json
import sys

path, side_path = sys.argv[1:3]
out = sys.argv[3] if len(sys.argv) > 3 else path
text = open(path).read()
plan = json.loads(text)
seps = next(sp for sp in ((", ", ": "), (",", ":")) if json.dumps(plan, separators=sp) + "\n" == text)
side = json.load(open(side_path))["collector"]["types"]
moved = {}
for tn, t in plan["partition_types"].items():
    c = (t.get("clock") or {}).get("landing_contract") or {}
    s = side.get(tn)
    if not s or not c.get("collector_children"):
        continue
    assert len(c["collector_children"]) == len(s["children"]), tn
    for a, b in zip(c["collector_children"], s["children"]):
        assert (a["index"], a["part"], a["xy_um"]) == (b["index"], b["part"], b["xy_um"]), (tn, a, b)
        if a["node"] != b["node"]:
            moved.setdefault(tn, []).append([a["part"], a["node"], b["node"]])
            a["node"] = b["node"]
open(out, "w").write(json.dumps(plan, separators=seps) + "\n")
print(len(moved), "types", sum(map(len, moved.values())), "children")
for tn in sorted(moved):
    print(" ", tn, moved[tn])
