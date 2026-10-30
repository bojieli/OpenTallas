#!/usr/bin/env python3
"""DIE-S81-30 (COORD 14:5x approved ASK): bumps.anchor=rect on ALL die.pg.domains (one fix-only PG event) on the
WS3 V2 + a45 plan copy (plan_s13r2_ws3v2_pga45.json sha f2d1e153..); same pitch/count basis, no metal change.
    python3 rect14.py IN.json OUT.json  -> prints per-domain IR windows (rect + 86.4 um margin)"""
import json, sys
src, dst = sys.argv[1:3]
p = json.load(open(src))
W, H = p["die"]["outline_um"]
for d in p["die"]["pg"]["domains"]:
    d["bumps"]["anchor"] = "rect"
    d["note"] = d.get("note", "") + "; DIE-S81-30 rect-anchored PHY C4 (all-domain PG event)"
json.dump(p, open(dst, "w"))
M = 86.4
for d in p["die"]["pg"]["domains"]:
    r = d["rect_um"]
    print(d["name"], max(0, r[0]-M), max(0, r[1]-M), min(W, r[2]+M), min(H, r[3]+M))
