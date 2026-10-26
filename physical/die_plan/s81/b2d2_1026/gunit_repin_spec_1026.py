#!/usr/bin/env python3
"""PATH-S81-R3 D-S81-B2: gunit core re-pin spec for the S81-CORE-LAT 12.8 rebuilds (GEOM-REVIEW-17 B2-D1 cond 1).
Input = gunit_faces_1026.py output (every face-away port group, reach lower bound to its partner core).  MUST = reach
lower bound > 405 um (blocks the gunit kit); SHOULD = face-away but <= 405 (re-pin in the same rebuild; one rebuild,
top-down pins).  Faces are in the gunit type frame (cores are R180 there): the core-frame face is given too.
usage: gunit_repin_spec_1026.py FACES.json PLAN.json OUT.json"""
import json, sys
faces, plan, out = sys.argv[1:4]
t = json.load(open(plan))["partition_types"]["gunit__t1_phy1026_gunit"]
orient = {h["inst"]: (h.get("orient", "R0"), h["module"]) for h in t["hard_cores"]}
FLIP = {"R0": {}, "R180": dict(N="S", S="N", E="W", W="E"), "MX": dict(N="S", S="N"), "MY": dict(E="W", W="E")}
rows = []
for r in json.load(open(faces)):
    o, mod = orient[r["core"]]
    f = FLIP[o]
    rows.append(dict(r, module=mod, orient=o, core_frame_face_now=f.get(r["face"], r["face"]),
                     core_frame_face_to=f.get(r["repin_to"], r["repin_to"]),
                     cls="MUST" if (r["reach_lb_um"] or 0) > 405 else "SHOULD"))
json.dump(dict(type="gunit__t1_phy1026_gunit", rule="GEOM-REVIEW-17 B2-D1 cond 1; 12.8a centre clock entry at core centre",
               groups=rows, must=sum(r["cls"] == "MUST" for r in rows), should=sum(r["cls"] == "SHOULD" for r in rows)),
          open(out, "w"), indent=1)
from collections import Counter
print(Counter((r["module"], r["cls"]) for r in rows))
