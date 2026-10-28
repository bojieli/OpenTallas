#!/usr/bin/env python3
"""DIE-HBM-4-KITS 10-28: plan pin delta for ot_hfd_coll_q2_hard_v8g__ring_ag (GEOM-REVIEW-40 [AUTO-GEOM 68d657fa5a42]).
  apply_q2_qid_mid.py PLANDIR [--target-y 116.64] [--report OUT.json]
qid[1:0] (ring node ID, read by flit build at the E face and by the rx comparators) sits at the SW corner of the
W face (y 9.096/9.336) -> one-hop r2r 425 um to the NE out_p regs.  The W face (M4, x 0.096) is full: every
M4 track site from y 8.808 to 224.472 is used, so qid cannot take a free site.  Delta = order-preserving
rotation along the W face: qid[0], qid[1] move to the two W-face sites nearest --target-y (face middle), and the
pins between their old and new sites each move down by exactly two sites (<= 0.58 um, same order, same layer,
same lattice sites).  No pin leaves the W face, no site is invented, no other face is touched.
Edits PLANDIR/<pins_file> in place (run on a COPY of the plan dir) and writes a report."""
import json, sys, hashlib, argparse
from pathlib import Path
ap = argparse.ArgumentParser(); ap.add_argument("plan"); ap.add_argument("--target-y", type=float, default=116.64)
ap.add_argument("--report", default=None); a = ap.parse_args()
PF = "cores/ot_hfd_coll_q2_hard_v8g__ring_ag__233.28x233.28__q_hub_u_hb_coll_Q_ring_ag__oneclk.json"
p = Path(a.plan) / PF
sha = lambda b: hashlib.sha256(b).hexdigest()
raw = p.read_bytes(); pins = json.loads(raw)
west = sorted([q for q in pins if q["x"] < 1.0], key=lambda q: q["y"])
sites = [(q["x"], q["y"], q["layer"]) for q in west]
names = [q["name"] for q in west]
if names.index("qid[1]") != names.index("qid[0]") + 1:
    raise SystemExit("qid[1:0] not on adjacent W-face sites: delta form does not apply")
i0 = names.index("qid[0]")
k = min(range(len(sites)), key=lambda i: abs(sites[i][1] - a.target_y))   # first qid site at the face middle
if k <= i0 + 1:
    raise SystemExit("target not above the current qid sites")
order = names[:i0] + names[i0 + 2:k + 2]           # pins that were between move down 2 sites
order = order[:k] + ["qid[0]", "qid[1]"] + order[k:] + names[k + 2:]
assert sorted(order) == sorted(names) and len(order) == len(sites)
byname = {q["name"]: q for q in pins}
moves = []
for nm, (x, y, ly) in zip(order, sites):
    q = byname[nm]
    if (q["x"], q["y"], q["layer"]) != (x, y, ly):
        moves.append(dict(name=nm, from_xy=[q["x"], q["y"]], to_xy=[x, y], dy=round(y - q["y"], 3)))
        q["x"], q["y"], q["layer"] = x, y, ly
out = json.dumps(pins, indent=1) + "\n"
p.write_text(out)
others = [m for m in moves if not m["name"].startswith("qid[")]
rep = dict(schema="opentallas.hbm.plan_pin_delta.v1", lane="DIE-HBM-4-KITS", review="GEOM-REVIEW-40 [AUTO-GEOM 68d657fa5a42]",
           module="ot_hfd_coll_q2_hard_v8g__ring_ag", pins_file=PF, sha_before=sha(raw), sha_after=sha(out.encode()),
           pins=len(pins), west_sites=len(sites), target_y=a.target_y,
           qid=[m for m in moves if m["name"].startswith("qid[")],
           others_moved=len(others), others_max_abs_dy_um=max((abs(m["dy"]) for m in others), default=0.0),
           others_range=[others[0]["name"], others[-1]["name"]] if others else [],
           note="order-preserving W-face rotation; no new site, no face/layer change")
if a.report:
    Path(a.report).write_text(json.dumps(dict(rep, moves=moves), indent=1) + "\n")
print(json.dumps(rep))
