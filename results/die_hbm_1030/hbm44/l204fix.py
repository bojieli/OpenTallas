#!/usr/bin/env python3
"""DIE-HBM-44: L204/L204m same-count station re-site. The b010|b001 seam pin (only free spot: L14/L11 fill the face
beside the old stations) is kept; b010 gets its LAST station and b001 its FIRST station on the nearest macro-free
lattice point >= 8.64 um inside the outline to that pin (seam hop = d1 + d2), the other stations are re-solved by station_resite.route (macro-free
4.32 lattice + halo, every hop <= reach) between the in pin and that point. Count unchanged unless no solution.
usage: l204fix.py PLAN_DIR OUT_DIR"""
import json, sys, os, hashlib
from pathlib import Path
import numpy as np
sys.path.insert(0, "/srv/opentallas-scratch2/claude/wt/die-hbm-42/tools/die_plan")
import station_resite as SR, hub_repack as HR
src, out = Path(sys.argv[1]), Path(sys.argv[2])
p = json.loads((src / "die_plan.json").read_text()); T = p["partition_types"]
REACH = float(os.environ.get("REACH", 395.0))
rep = {"schema": "opentallas.die_hbm_44.l204fix.v1", "base_sha256": hashlib.sha256((src / "die_plan.json").read_bytes()).hexdigest(), "reach_um": REACH, "slots": []}
def pinpt(s, io, face, outline):
    w = s[io + "_window_um"]; c = (w[0] + w[1]) / 2
    return {"W": (0.0, c), "E": (outline[0], c), "S": (c, 0.0), "N": (c, outline[1])}[face]
def nearest_free(free, pt, maxd=150, edge=8.64):
    G = SR.G; nx, ny = free.shape
    best = None
    for i in range(max(0, int((pt[0] - maxd) // G)), min(nx, int((pt[0] + maxd) // G) + 2)):
        for j in range(max(0, int((pt[1] - maxd) // G)), min(ny, int((pt[1] + maxd) // G) + 2)):
            if free[i, j] and edge - 1e-6 <= i * G <= (nx - 1) * G - edge + 1e-6 and edge - 1e-6 <= j * G <= (ny - 1) * G - edge + 1e-6:
                d = abs(i * G - pt[0]) + abs(j * G - pt[1])
                if best is None or d < best[0]: best = (d, (round(i * G, 3), round(j * G, 3)))
    return best
for ta, sa, tb, sb in (("q_b010__physical_v1", "L204x1", "q_b001__physical_v1", "L204x2"), ("q_b010", "L204mx1", "q_b001", "L204mx2")):
    A = [x for x in T[ta]["ft_slots"] if x["name"] == sa][0]; B = [x for x in T[tb]["ft_slots"] if x["name"] == sb][0]
    fa = {}
    for tn in (ta, tb):
        rects = SR.core_rects(T[tn]); fa[tn] = HR.Raster(*T[tn]["outline_um"], [r[1:] for r in rects]).f
    ain = pinpt(A, "in", A["in_face"], T[ta]["outline_um"]); aout = pinpt(A, "out", A["out_face"], T[ta]["outline_um"])
    bin_ = pinpt(B, "in", B["in_face"], T[tb]["outline_um"]); bout = pinpt(B, "out", B["out_face"], T[tb]["outline_um"])
    d1, q = nearest_free(fa[ta], aout); d2, r = nearest_free(fa[tb], bin_)
    nA, nB = len(A["regs_um"]), len(B["regs_um"])
    resA = resB = None
    for k in range(nA - 1, nA + 2):
        resA = SR.route(fa[ta], ain, q, k, REACH) if k > 0 else []
        if resA is not None: kA = k; break
    for k in range(nB - 1, nB + 2):
        resB = SR.route(fa[tb], r, bout, k, REACH) if k > 0 else []
        if resB is not None: kB = k; break
    newA = resA + [list(q)]; newB = [list(r)] + resB
    row = dict(a=f"{ta}.{sa}", b=f"{tb}.{sb}", seam_hop_um=round(d1 + d2, 1), d1=d1, d2=d2,
               a_old=A["regs_um"], a_new=newA, b_old=B["regs_um"], b_new=newB, a_count=[nA, len(newA)], b_count=[nB, len(newB)])
    rep["slots"].append(row); print(json.dumps({k: v for k, v in row.items() if "old" not in k and "new" not in k}))
    A["regs_um"] = newA; B["regs_um"] = newB; A["stations"] = len(newA); B["stations"] = len(newB)
    for s, tag in ((A, "last"), (B, "first")):
        s["note"] = s.get("note", "") + f" | DIE-HBM-44: {tag} station at the seam pin, rest re-solved (station_resite.route, reach {REACH})"
out.mkdir(parents=True, exist_ok=True)
for f in os.listdir(src):
    if f == "die_plan.json" or (out / f).exists(): continue
    os.symlink(os.path.realpath(src / f), out / f)
(out / "die_plan.json").write_text(json.dumps(p, indent=1) + "\n")
rep["plan_sha256"] = hashlib.sha256((out / "die_plan.json").read_bytes()).hexdigest()
(out / "l204fix_report.json").write_text(json.dumps(rep, indent=1) + "\n")
print(rep["plan_sha256"])
