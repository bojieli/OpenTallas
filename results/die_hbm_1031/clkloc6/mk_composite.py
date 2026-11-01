#!/usr/bin/env python3
"""HBM-CLKLOC-6: composite die proof = die-tree proof (e.g. C10i) with the hub parts' taps replaced by the routed hub-MESH
hub-only proof (HUBMESH-6 a3e6s GRT-RC, mk_hubproof + addearly).  Hub tap arrival = die-tree arrival of the hub region
node (where the die feed reaches the hub region; mesh root = hub plan entry) + mesh arrival from the mesh root + SHIFT_ps.
Feed-through legs of the hub region to its child regions stay on the die tree (their arrivals unchanged).
usage: mk_composite.py DIE_PROOF OUT_PROOF PART:REGION:HUBPROOF_DIR [...] [--shift PS]"""
import json, shutil, sys
from pathlib import Path
a = sys.argv[1:]; shift = 0.0
if "--shift" in a:
    i = a.index("--shift"); shift = float(a[i + 1]); del a[i:i + 2]
src, out = Path(a[0]), Path(a[1]); out.mkdir(parents=True, exist_ok=True)
hubs = [s.split(":") for s in a[2:]]
for f in src.iterdir():
    if f.is_file() and not f.name.startswith("tap_arrivals_"):
        shutil.copy(f, out / f.name)
for C in ("TT", "FF"):
    P = json.load(open(src / f"tap_arrivals_{C}.json"))
    for part, reg, hp in hubs:
        H = json.load(open(Path(hp) / f"tap_arrivals_{C}.json"))
        base = P["node_late_ps"][reg] + shift
        old = {t["port"]: t for t in P["taps"] if t["part"] == part}
        new = {t["port"]: t for t in H["taps"]}
        if set(old) != set(new):
            raise SystemExit(f"{part}: port sets differ: die-only {len(set(old)-set(new))} mesh-only {len(set(new)-set(old))}")
        keep = [t for t in P["taps"] if t["part"] != part]
        for p, t in new.items():
            o = old[p]
            v = base + t["late_ps"]
            keep.append(dict(o, late_ps=v, early_ps=v, slew_ps=t["slew_ps"], cppr_node=reg,
                             stages_from_root=P["node_stages"][reg], xy_um=t["xy_um"], tree_path=o.get("tree_path"),
                             hub_mesh=dict(mesh_ps=t["late_ps"], entry_node=reg, entry_ps=P["node_late_ps"][reg], shift_ps=shift)))
        P["taps"] = keep
        print(C, part, reg, "entry", round(P["node_late_ps"][reg], 1), "mesh", round(min(t["late_ps"] for t in new.values()), 1),
              round(max(t["late_ps"] for t in new.values()), 1), "die old", round(min(t["late_ps"] for t in old.values()), 1),
              round(max(t["late_ps"] for t in old.values()), 1))
    P["basis"] = P.get("basis", "") + f" | HBM-CLKLOC-6 composite: hub taps {[h[0] for h in hubs]} = die node + routed hub mesh (GRT-RC, FF=TTx0.8666 UNCHECKED) shift {shift}"
    json.dump(P, open(out / f"tap_arrivals_{C}.json", "w"))
