#!/usr/bin/env python3
"""CLOCK-KV-R22 plan delta: declared landing island for the KV PHY->PHY ft0 relay (COORD RULING CLOCK-KV-R21 ASK1).

The die_sta hold demand (CLOCK-KV-R21 hold_demand_die_sta.json) leaves kv3_phy_v1 ft0 PHY->PHY 'unplaced': sender
and receiver are both kv3_phy_v1 (hard PHY partition, no P&R kit).  This adds ONE declared landing island to the
kv3_phy_v1 type at its ft0_i face pin (type frame; every instance, type-hardened k = max over the 24 receivers), sized
for bits x k HB4, owner die_top.  Every receiver instance's die-frame ft0 window must map to the same type-frame x
(orientation check), else refuse.
usage: landing_island_delta.py PLAN.json DEMAND_TYPE.json DEMAND_FULL.json.gz OUT_PLAN.json OUT_DELTA.json"""
import gzip
import hashlib
import json
import sys
from pathlib import Path

import landing_islands as LI
import schema as S

TYPE, SLOT = "kv3_phy_v1", "ft0"


def main(argv=None):
    a = (argv or sys.argv[1:])
    plan, dtype, dfull, out_plan, out_delta = a
    raw_b = Path(plan).read_bytes()
    raw = json.loads(raw_b)
    P = S.Plan(raw)
    D = json.loads(Path(dtype).read_text())
    un = D["unplaced"][TYPE][SLOT + "_o"]
    bits = len(un)
    k = max(int(v[0]) for v in un.values())
    dmax = max(float(v[1]) for v in un.values())
    full_sha = hashlib.sha256(gzip.open(dfull).read() if dfull.endswith(".gz") else Path(dfull).read_bytes()).hexdigest()
    # receiver instances = lanes ports into <TYPE>.<SLOT>_i from <TYPE>.<SLOT>_o
    xs, rec = set(), []
    t = raw["partition_types"][TYPE]
    face, _ = LI.port_face(t, SLOT + "_i")
    for pid, pr in P.ports.items():
        if pr["dst"]["bus"] != SLOT + "_i" or P.ptype(pr["dst"]["part"]) is not t:
            continue
        src_t = P.parts[pr["src"]["part"]]["type"] if pr["src"]["part"] in P.parts else None
        lo, hi = pr["window_um"]
        r = P.rect(pr["dst"]["part"])
        die_face = {"N": "S", "S": "N", "E": "W", "W": "E"}[pr["face"]]   # port face = the sender's out face
        # die point on the face of the receiver
        if die_face in ("N", "S"):
            pts = [P.to_type(pr["dst"]["part"], (lo, r[1])), P.to_type(pr["dst"]["part"], (hi, r[1])),
                   P.to_type(pr["dst"]["part"], (lo, r[3])), P.to_type(pr["dst"]["part"], (hi, r[3]))]
        else:
            raise SystemExit(f"{pid}: E/W face not handled")
        tx = tuple(sorted({round(p[0], 4) for p in pts}))
        xs.add(tx)
        rec.append(dict(port=pid, dst=pr["dst"]["part"], src=pr["src"]["part"], src_type=src_t, die_face=die_face,
                        type_face=P.type_face(pr["dst"]["part"], die_face), type_window_x=list(tx)))
    if len(xs) != 1:
        raise SystemExit(f"receiver ft0 windows map to {len(xs)} different type-frame x ranges: {sorted(xs)}")
    if any(x["type_face"] != face for x in rec):
        raise SystemExit(f"a receiver enters on a type face != slot in_face {face}: {rec}")
    win = list(next(iter(xs)))
    isl = LI.propose(t, SLOT + "_i", win, bits, k,
                     dict(source="die_sta hold demand (CLOCK-KV-R21 hold_demand_die_sta.py, unplaced kv3_phy_v1 ft0)",
                          sha256=full_sha, ff_hold_ps=round(-dmax, 3), demand_ps=dmax))
    t2 = dict(t)
    t2["landing_islands"] = list(t.get("landing_islands") or []) + [isl]
    raw["partition_types"][TYPE] = t2
    errs = LI.check(raw)
    s = json.dumps(raw, indent=1)
    Path(out_plan).write_text(s)
    delta = dict(lane="CLOCK-KV-R22", delta="D-KV-LAND-FT0", base_plan=plan,
                 base_plan_sha256=hashlib.sha256(raw_b).hexdigest(),
                 out_plan_sha256=hashlib.sha256(s.encode()).hexdigest(), type=TYPE, island=isl,
                 receivers=rec, phy_to_phy_receivers=sum(1 for x in rec if x["src_type"] == TYPE),
                 instances_of_type=sum(1 for p in raw["partitions"] if p["type"] == TYPE),
                 capacity_cells=LI.capacity(isl["rect_um"], "HB4xp67_ASAP7_75t_R"), check_errors=errs,
                 plan_width_bits={x["port"]: P.ports[x["port"]]["width"] for x in rec})
    Path(out_delta).write_text(json.dumps(delta, indent=1))
    print(json.dumps(dict(island=isl["rect_um"], cells=isl["cells"], receivers=len(rec),
                          phy_to_phy=delta["phy_to_phy_receivers"], window_x=win, errs=errs,
                          out=delta["out_plan_sha256"][:8])))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
