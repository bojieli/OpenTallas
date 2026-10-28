#!/usr/bin/env python3
"""DIE-S81-5: reconcile each lk_* SerDes partition: ot_pdie_serdes macro (type contents) vs die.pg.domains phy_lk_* rect,
and list R4 grid taps that sit over the macro / domain.  usage: serdes_recon.py WT PLAN"""
import json, sys
from pathlib import Path
WT, PL = sys.argv[1], sys.argv[2]
sys.path.insert(0, WT + "/tools/die_plan")
import schema as S, gen_phys
P = S.Plan(S.load(PL), Path(PL))
dom = {d["name"]: d["rect_um"] for d in P.die["pg"]["domains"]}
out = {}
for n in sorted(x for x in P.parts if x.startswith("lk_")):
    tn = P.parts[n]["type"]; t = P.types[tn]; W, H = t["outline_um"]
    c = [c for c in t.get("contents", []) if c.get("module") == "ot_pdie_serdes"]
    ox, oy = P.parts[n]["origin_um"]
    prt = (ox, oy, ox + W, oy + H)
    mac = None
    if c and c[0].get("origin_um"):
        (x, y), (w, h) = c[0]["origin_um"], c[0]["outline_um"]
        a, b = P.to_die(n, (x, y)), P.to_die(n, (x + w, y + h))
        mac = (min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]))
    d = dom.get("phy_" + n)
    taps = [(p, *P.to_die(n, (x, y))) for p, x, y in gen_phys.clock_pins(P, tn)]
    inside = lambda r, q: r and r[0] < q[0] < r[2] and r[1] < q[1] < r[3]
    rec = dict(type=tn, orient=P.orient(n), part=[round(v, 3) for v in prt], macro=mac and [round(v, 3) for v in mac],
               domain=d, taps=len(taps), taps_over_macro=sum(1 for q in taps if inside(mac, q[1:])),
               taps_over_domain=sum(1 for q in taps if inside(d, q[1:])))
    if mac and d:
        rec["domain_minus_macro_um"] = [round(mac[0] - d[0], 3), round(mac[1] - d[1], 3), round(d[2] - mac[2], 3), round(d[3] - mac[3], 3)]
        rec["domain_is_whole_partition"] = all(abs(a - b) < 1 for a, b in zip(d, prt))
    out[n] = rec
    print(n, json.dumps(rec))
