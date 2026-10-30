#!/usr/bin/env python3
"""DIE-S81-30 fix-only PG correction for phy_lk_ES0/ES1 (COORD 15:3x): their bumps.rect_um / PHY io rect still sit at the
pre-flip slot (y 103.68), but the placed u_phy (partition contents origin (63.64,302.4) 2608.48x924.48, partition orient MY)
lies at y 406.08..1330.56 inside the unchanged domain rect (y0 342.44, +63.64 guard as WS3/EN0); the core strip
(boundary flops + 512-bit ft stations, ft windows y 6..452 local) is y 103.68..342.44. Same pattern as EN0/WS3:
phy_macro_um = placed u_phy, bumps.rect_um = placed u_phy, core_strip_um = partition - domain rect. Domain rect unchanged.
    python3 es_fix.py IN.json OUT.json"""
import json, sys
src, dst = sys.argv[1:3]
p = json.load(open(src))
T = p["partition_types"]; T = T if isinstance(T, dict) else {t["name"]: t for t in T}
P = {q["name"]: q for q in p["partitions"]}
for d in p["die"]["pg"]["domains"]:
    if d["name"] not in ("phy_lk_ES0", "phy_lk_ES1"):
        continue
    q = P[d["name"][4:]]; t = T[q["type"]]
    c = t["contents"]; c = json.loads(c) if isinstance(c, str) else c
    u = next(x for x in c if x["inst"] == "u_phy")
    W, H = t["outline_um"]; (ox, oy), (lx, ly), (w, h) = q["origin_um"], u["origin_um"], u["outline_um"]
    assert q.get("orient") == "MY", q.get("orient")
    phy = [round(ox + W - lx - w, 4), round(oy + ly, 4), round(ox + W - lx, 4), round(oy + ly + h, 4)]
    r = d["rect_um"]; part = [ox, oy, ox + W, oy + H]
    assert r[0] <= phy[0] and r[1] <= phy[1] and r[2] >= phy[2] and r[3] >= phy[3], (r, phy)
    strip = [[part[0], part[1], part[2], r[1]]]
    if r[0] > part[0]: strip.append([part[0], r[1], r[0], part[3]])
    if r[2] < part[2]: strip.append([r[2], r[1], part[2], part[3]])
    print(d["name"], "old bumps", d["bumps"]["rect_um"], "old phy", d.get("phy_macro_um"), "old strip", d.get("core_strip_um"))
    d["phy_macro_um"] = phy; d["bumps"]["rect_um"] = list(phy); d["core_strip_um"] = [[round(v, 4) for v in s] for s in strip]
    d["note"] = d.get("note", "") + "; DIE-S81-30 ES fix-only: bumps/phy_macro_um moved to the placed u_phy (MY), core_strip_um = partition - domain"
    print(d["name"], "new phy/bumps", phy, "strip", d["core_strip_um"], "domain", r)
json.dump(p, open(dst, "w"))
