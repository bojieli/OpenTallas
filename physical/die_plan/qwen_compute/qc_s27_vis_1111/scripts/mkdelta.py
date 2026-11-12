#!/usr/bin/env python3
"""Positions/stations-only delta of CAND vs BASE for the listed types: {"partition_types": {T: {"hard_cores": [...],
"ft_slots": [...]}}} plus a compact per-core / per-slot change list (inst -> origin/orient; slot -> regs_um/bit_sites).
Asserts nothing else in the type changed.     mkdelta.py BASE CAND TYPES(comma or json files) OUT"""
import json, sys
b, c, tl, out = sys.argv[1:5]
B = json.load(open(b)); C = json.load(open(c))
types = [t for f in tl.split(",") for t in (json.load(open(f)) if f.endswith(".json") else [f])]
D = {"schema": "opentallas.qc_vis_resite_delta.v1", "fields": ["hard_cores[].origin_um", "hard_cores[].orient",
     "ft_slots[].regs_um"], "partition_types": {}, "changes": {}}
for tn in types:
    x = B["partition_types"][tn]; y = C["partition_types"][tn]
    other = [k for k in set(x) | set(y) if k not in ("hard_cores", "ft_slots") and x.get(k) != y.get(k)]
    assert not other, (tn, other)
    ch = {"cores": {}, "slots": {}}
    for p, q in zip(x["hard_cores"], y["hard_cores"]):
        assert p["inst"] == q["inst"]
        d = {k for k in set(p) | set(q) if p.get(k) != q.get(k)}
        assert d <= {"origin_um", "orient"}, (tn, p["inst"], d)
        if d:
            ch["cores"][q["inst"]] = {"origin_um": q["origin_um"], "orient": q.get("orient", "R0")}
    for p, q in zip(x.get("ft_slots") or [], y.get("ft_slots") or []):
        d = {k for k in set(p) | set(q) if p.get(k) != q.get(k)}
        assert d <= {"regs_um", "bit_sites_um"}, (tn, p["name"], d)
        if d:
            ch["slots"][q["name"]] = {k: q.get(k) for k in d}
    if ch["cores"] or ch["slots"]:
        D["partition_types"][tn] = {"hard_cores": y["hard_cores"], "ft_slots": y.get("ft_slots")}
        D["changes"][tn] = ch
open(out, "w").write(json.dumps(D, indent=1) + "\n")
print(len(D["partition_types"]), "types in delta")
