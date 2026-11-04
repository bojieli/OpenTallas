#!/usr/bin/env python3
"""DIE-QC-68 11-04: republish every stale QC landing collector_tree (class STALE COLLECTOR TREE, DIE-KV-65 hubwi form).

The reset tree solved from the plan moved (RED, y-shrink, CLAND re-sites), clock.landing_contract.collector_tree kept the
older snapshot: 86 of 88 differ from RT.for_type (SS26-TOK 04:23), strict die bind stops at the first absent raw reset
parent. bind reads the sidecar copy, so both files take the tree. Only collector_tree changes. A contract field change
(depth, own_depth, entry, taps, outs, n_clock_taps) is reported, not hidden.

    republish_collector_trees.py PLAN SIDECAR   (run from the repository root)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, "tools/die_plan")
import reset_tree as RT
import schema

GUARD = ("depth", "own_depth", "entry", "taps", "outs", "n_clock_taps")


def main(plan_path, side_path):
    p, q = Path(plan_path), Path(side_path)
    ptext, stext = p.read_text(), q.read_text()
    raw, side = json.loads(ptext), json.loads(stext)
    P = schema.Plan(raw, p)
    changed, moved = {}, {}
    for tn, t in raw["partition_types"].items():
        lc = (t.get("clock") or {}).get("landing_contract") or {}
        old = lc.get("collector_tree")
        if old is None:
            continue
        new = json.loads(json.dumps(RT.for_type(P, tn)))
        if new == old:
            continue
        diff = [k for k in GUARD if old.get(k) != new.get(k)]
        if diff:
            moved[tn] = {k: [old.get(k), new.get(k)] for k in diff}
        changed[tn] = [len(old.get("relays", [])), len(new.get("relays", []))]
        lc["collector_tree"] = new
        rec = side["collector"]["types"].get(tn)
        if rec is not None:
            rec["tree"] = new
    p.write_text(json.dumps(raw) + ("\n" if ptext.endswith("\n") else ""))
    fmt = {"indent": 1} if stext.startswith("{\n") else {}
    q.write_text(json.dumps(side, **fmt) + ("\n" if stext.endswith("\n") else ""))
    print(f"republished {len(changed)} trees; contract fields moved on {len(moved)} types")
    for tn, v in sorted(changed.items()):
        print(tn, "relays", v[0], "->", v[1], moved.get(tn, ""))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
