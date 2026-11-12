#!/usr/bin/env python3
"""apply a scorer_rows.py delta: append each type's internal_stations_add rows (positions only).
usage: apply_scorer.py PLAN_IN DELTA OUT_PLAN  (refuses when a row of the same conn+capture already exists)"""
import json
import sys

P = json.load(open(sys.argv[1]))
D = json.load(open(sys.argv[2]))
for tn, d in D["types"].items():
    t = P["partition_types"][tn]
    have = {(r.get("conn"), r.get("capture"), r.get("launch")) for r in t.get("internal_stations", [])}
    for r in d["internal_stations_add"]:
        k = (r["conn"], r["capture"], r["launch"])
        if k in have:
            raise SystemExit(f"{tn}: row {k} already present")
        bus = r["conn"][4:]
        n = max(len(x["regs_um"]) for x in t["internal_stations"] if x.get("conn") == r["conn"])
        if len(r["regs_um"]) != n:
            raise SystemExit(f"{tn} {bus}: row depth {len(r['regs_um'])} != bus depth {n}")
        # refresh the stale attribution: the other rows of this bus keep their positions; their bits are scaled
        # (largest remainder, >= 1 each) so the bus total stays what it was (the scorer row takes its own bits)
        others = [x for x in t["internal_stations"] if x.get("conn") == r["conn"]]
        tot = sum(int(x.get("bits", 1)) for x in others)
        keep = max(tot - int(r["bits"]), len(others))
        raw = [int(x.get("bits", 1)) * keep / tot for x in others]
        new = [max(1, int(v)) for v in raw]
        for i in sorted(range(len(others)), key=lambda i: -(raw[i] - int(raw[i]))):
            if sum(new) >= keep:
                break
            new[i] += 1
        for x, v in zip(others, new):
            if int(x.get("bits", 1)) != v:
                x["note"] = (str(x.get("note", "")) + f" | DIE-LAYOUT-HBM SCORER 11-11: bits {int(x.get('bits', 1))} -> {v} "
                             f"(bound RTL: scorer group owns {r['bits']} b of this bus)").lstrip(" |")
                x["bits"] = v
        t["internal_stations"].append(r)
        print(tn, bus, "rows", len(others), "bits", tot, "->", sum(new), "+ scorer", r["bits"])
json.dump(P, open(sys.argv[3], "w"), indent=1)
