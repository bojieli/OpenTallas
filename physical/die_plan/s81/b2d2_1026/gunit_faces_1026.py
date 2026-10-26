#!/usr/bin/env python3
"""PATH-S81-R3: full list of face-away core ports for one type (check_core_faces, unlimited messages) + reach lower
bound per group (min Manhattan from the port's pins to its partner core box).  usage: SRC PLAN CONNS TYPE OUT.json"""
import json, re, sys
from pathlib import Path
SRC, PLAN, CONNS, TN, OUT = sys.argv[1:6]
sys.path[:0] = [SRC + "/tools/die_plan"]
import schema as S, check as C
raw = S.load(PLAN)
raw["partition_types"] = {TN: raw["partition_types"][TN]}
pd = Path(PLAN).resolve().parent
P = S.Plan(raw, pd / "die_plan.json")
R = C.Report(True)
C.check_core_faces(P, R, plan_dir=pd, conns_file=CONNS, max_msgs=10000)
t = raw["partition_types"][TN]
hcs = {h["inst"]: h for h in t["hard_cores"]}
def box(h):
    (x, y), (w, hh) = h["origin_um"], h["outline_um"]; return x, y, x + w, y + hh
rows = []
for it in R.items:
    m = re.match(r"type \S+ core (\S+) port (\S+): (\d+) pins on face (\S+) face away from its partner\(s\) (.*?): mean cos ([-+.\d]+), (\d+) pins on the far side \(re-pin to face (\w+)\)", it["msg"] if isinstance(it, dict) else it.msg)
    if not m:
        continue
    ci, port, n, face, part, cos, away, to = m.groups()
    hc = hcs[ci]; cw, ch = hc["outline_um"]; ox, oy = hc["origin_um"]
    pts = [C._orient_pt(hc.get("orient", "R0"), cw, ch, x, y) for nm, ln, x, y in C.core_pins(hc, pd) if re.sub(r"\[\d+\]$", "", nm) == port]
    lb = None
    for p in [q.strip() for q in part.split(",")]:
        if p in hcs:
            bx = box(hcs[p])
            d = min(max(0, bx[0] - (ox + a), (ox + a) - bx[2]) + max(0, bx[1] - (oy + b), (oy + b) - bx[3]) for a, b in pts)
            lb = d if lb is None else min(lb, d)
    rows.append(dict(core=ci, port=port, pins=int(n), face=face, partners=part, mean_cos=float(cos), repin_to=to,
                     reach_lb_um=None if lb is None else round(lb, 1)))
Path(OUT).write_text(json.dumps(rows, indent=1) + "\n")
print(len(rows), "groups;", sum(r["pins"] for r in rows), "pins; >405:", sum(1 for r in rows if (r["reach_lb_um"] or 0) > 405))
from collections import Counter
print(Counter((r["core"], r["repin_to"]) for r in rows).most_common(20))
print("max lb", max((r["reach_lb_um"] or 0) for r in rows))
