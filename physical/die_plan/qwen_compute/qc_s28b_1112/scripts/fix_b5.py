#!/usr/bin/env python3
"""QC-S28-B B2 pass-2 repairs after the s28b4 gates (G0 / bind findings):
 (1) restore landing_contract START pins (cland_tstart_in / cland_tstart_out / cland_raw_reset_out) to BASE: they are
     interior M7 over-the-top pins the die START provider (clock.landing_network.start_tree.provider) binds by
     geometry; the legalize band remap slid them 9.75-23.5 um -> G0 'boundary pin geometry mismatch'
 (2) revert the types in --revert to BASE (whole type)
 (3) --snap: hard-core origins off the 8.64-um lattice are snapped to the nearest lattice point in the direction the
     legalize moved them (away from the base origin), keeping the street width >= the legalized one
   fix_b5.py BASE.json CAND.json OUT.json REPORT.json --revert T1,T2 [--snap]"""
import copy, json, sys
GRID = 8.64
START_PINS = ("cland_tstart_in", "cland_tstart_out", "cland_raw_reset_out")
base, cand, out, rep = sys.argv[1:5]
rev = sys.argv[sys.argv.index("--revert") + 1].split(",") if "--revert" in sys.argv else []
snap = "--snap" in sys.argv
A, B = json.load(open(base)), json.load(open(cand))
R = dict(start_pins=[], reverted=rev, snapped=[])
for tn in rev:
    B["partition_types"][tn] = copy.deepcopy(A["partition_types"][tn])
for tn, t in B["partition_types"].items():
    t0 = A["partition_types"][tn]
    if t == t0:
        continue
    p0 = {q["name"]: q for q in t0["clock"].get("landing_contract", {}).get("pins", [])}
    for q in t["clock"].get("landing_contract", {}).get("pins", []):
        if q["name"] in START_PINS and q["name"] in p0 and q != p0[q["name"]]:
            R["start_pins"].append(dict(type=tn, pin=q["name"], cand=q["xy_um"], base=p0[q["name"]]["xy_um"]))
            b0 = copy.deepcopy(p0[q["name"]]); q.clear(); q.update(b0)
    if snap:
        c0 = {c["inst"]: c for c in t0.get("hard_cores", [])}
        for c in t.get("hard_cores", []):
            o = list(c["origin_um"]); b = c0.get(c["inst"], {}).get("origin_um", o)
            n = []
            for v, v0 in zip(o, b):
                k = v / GRID
                if abs(k - round(k)) <= 1e-6:
                    n.append(v); continue
                import math
                n.append(round((math.ceil(k) if v > v0 else math.floor(k)) * GRID, 4))
            if n != o:
                R["snapped"].append(dict(type=tn, core=c["inst"], cand=o, snapped=n, base=b))
                c["origin_um"] = n
print(len(R["start_pins"]), "START pins restored;", len(R["snapped"]), "cores snapped;", len(rev), "types reverted")
for s in R["snapped"]:
    print("  snap", s)
open(out, "w").write(json.dumps(B, indent=1) + "\n")
json.dump(R, open(rep, "w"), indent=1)
