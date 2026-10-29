#!/usr/bin/env python3
"""DIE-HBM-21 diag: nets whose box straddles cut (H: x=C) and whose y-span overlaps [A0,A1]; share of crossing in window
(approx: capacity uniform outside macros). usage: hotnets.py TOOLS GEOM C A0 A1"""
import sys, collections
sys.path.insert(0, sys.argv[1]); import geom_rules as G
D = G.Design(sys.argv[2]); C, A0, A1 = map(float, sys.argv[3:6])
idx = {}
for i, (sig, dr, sk) in enumerate(D.nets): pass
boxes = G._net_boxes(D)
# rebuild name list parallel to boxes
names = []
for sig, dr, sk in D.nets:
    if sig == "CLOCK": continue
    names.append((sig, dr, sk))
tot = 0; rows = []
for (x0, y0, x1, y1), (sig, dr, sk) in zip(boxes, names):
    if not (x0 < C < x1): continue
    ov = max(0.0, min(y1, A1) - max(y0, A0))
    if ov <= 0 and not (y0 == y1 and A0 <= y0 <= A1): continue
    span = max(y1 - y0, 1.0)
    w = max(ov, 1.0 if y0 == y1 else ov) / span
    # driver name
    dn = "?"
    if dr and dr[0] == "i" and dr[1] in D.cells: dn = D.cells[dr[1]][6]
    elif dr and dr[0] == "p": dn = "PIN " + D.pin_by_k[dr[1]]["name"]
    rows.append((w, dn, round(x0,1), round(y0,1), round(x1,1), round(y1,1), len(sk)))
    tot += w
rows.sort(reverse=True)
print("nets", len(rows), "est crossings in window", round(tot, 1))
grp = collections.Counter()
for r in rows:
    import re as _re; k=_re.sub(r"(\\\[|\[)\d+.*","",r[1]); k=k.split("/")[0]; k=_re.sub(r"_\d+_$|place\d+$|\$.*","",k); grp[k] += r[0]
for k, v in grp.most_common(12): print(f"{v:7.1f} {k}")
for r in rows[:25]: print(r)
