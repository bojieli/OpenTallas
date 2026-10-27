#!/usr/bin/env python3
"""HEAD-CORE-LAT-R7: elemB die pins file r7 = R6 pins file + the two GEOM-REVIEW-9 (a) conditions.
 (1) E face: every pin left on the OLD 277.652 edge (x 277.61) moves onto the 285.12 outline edge (x = 285.12 - 0.042),
     same y and layer (the R6 kit io.tcl moved the outline but not the E pins).
 (2) o_d unsplit: the o_d bits still on E move to the S face directly after the S o_d group, same 0.192 pitch, on free
     S-face sites (no other pin within 0.096 um); hd_tile has no E-side o_d consumer (consumers u_eA2/A3 are S of u_eB).
usage: r7_elemB_pins.py PINS_R6.json OUT.json      PLAN DATA, numbers UNCHECKED"""
import json, sys
src, out = sys.argv[1:3]
S, OLD_E, HALF = 285.12, 277.652, 0.042
d = json.load(open(src))
pins = d["pins"]
moved_e, moved_s = [], []
for p in pins:
    if abs(p["x"] - (OLD_E - HALF)) < 0.01:
        p["x"] = round(S - HALF, 3)
        moved_e.append(p["name"])
sface = sorted(p["x"] for p in pins if p["y"] < 1.0)
od_s = sorted(p["x"] for p in pins if p["name"].startswith("o_d[") and p["y"] < 1.0)
od_e = sorted((p for p in pins if p["name"].startswith("o_d[") and p["y"] >= 1.0), key=lambda p: p["y"])
x = od_s[-1]
for p in od_e:
    x = round(x + 0.192, 3)
    while any(abs(x - q) < 0.096 for q in sface):
        x = round(x + 0.192, 3)
    assert x < S - 4.32, x
    p.update(layer="M5", x=x, y=HALF)
    sface.append(x)
    moved_s.append(p["name"])
d["source"] = ("HEAD-CORE-LAT-R7 r7_elemB_pins.py from " + src + ": E pins on the 285.12 edge (GEOM-REVIEW-9 a1), "
               "o_d all on S (a2)")
d["r7"] = dict(e_moved_to_edge=len(moved_e), o_d_moved_E_to_S=moved_s, numbers="UNCHECKED")
json.dump(d, open(out, "w"), indent=1)
open(out, "a").write("\n")
print("E->edge", len(moved_e), "o_d E->S", len(moved_s), "pins", len(pins))
