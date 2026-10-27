#!/usr/bin/env python3
"""HBM-MU-QUAD-7: re-site internal_stations registers whose chain has a hop > LIMIT (Manhattan, as check._hops_ok).
Register COUNT unchanged (no cycle change); endpoints (core pins / face windows) fixed. Regs go to free 4.32-um lattice
points (2.16 um clear of every hard core of the type, inside the type outline): first an even split of the from->to
L-path, then local relaxation of the worst hop. usage: relax_internal.py PLANDIR [LIMIT=400]"""
import json, sys, numpy as np
from pathlib import Path
d = Path(sys.argv[1]); LIM = float(sys.argv[2]) if len(sys.argv) > 2 else 400.0
G, CLEAR = 4.32, 2.16
p = json.loads((d / "die_plan.json").read_text())
md = lambda a, b: abs(a[0]-b[0]) + abs(a[1]-b[1])
def worst(pts): return max(md(a, b) for a, b in zip(pts, pts[1:]))
rep = dict(fixed=0, failed=[], chains_bad_before=0)
for tn, t in p["partition_types"].items():
    ist = t.get("internal_stations") or []
    W, H = t["outline_um"]
    BX = []
    for h in t.get("hard_cores", []):
        x, y = h["origin_um"]; w, hh = h["outline_um"]; dx, dy = h.get("track_offset_um", [0, 0]); BX.append((x+dx, y+dy, x+dx+w, y+dy+hh))
    inc = lambda q: any(b[0]+.5 < q[0] < b[2]-.5 and b[1]+.5 < q[1] < b[3]-.5 for b in BX)
    bad = [e for e in ist if worst([e["from_um"]] + e["regs_um"] + [e["to_um"]]) > LIM or any(inc(q) for q in e["regs_um"])]
    if not bad: continue
    rep["chains_bad_before"] += len(bad)
    xs = np.arange(G, W - G/2, G); ys = np.arange(G, H - G/2, G)
    X, Y = np.meshgrid(xs, ys); X = X.ravel(); Y = Y.ravel(); ok = np.ones(X.shape, bool)
    for h in t.get("hard_cores", []):
        x, y = h["origin_um"]; w, hh = h["outline_um"]; dx, dy = h.get("track_offset_um", [0, 0])
        ok &= ~((X > x+dx-CLEAR) & (X < x+dx+w+CLEAR) & (Y > y+dy-CLEAR) & (Y < y+dy+hh+CLEAR))
    F = np.column_stack((X[ok], Y[ok]))
    def snap(q):
        i = np.argmin(np.abs(F[:, 0]-q[0]) + np.abs(F[:, 1]-q[1])); return [round(float(F[i, 0]), 3), round(float(F[i, 1]), 3)]
    def best_between(a, b):
        s = np.maximum(np.abs(F[:, 0]-a[0]) + np.abs(F[:, 1]-a[1]), np.abs(F[:, 0]-b[0]) + np.abs(F[:, 1]-b[1]))
        i = np.argmin(s); return [round(float(F[i, 0]), 3), round(float(F[i, 1]), 3)]
    for e in bad:
        a, b, n = e["from_um"], e["to_um"], len(e["regs_um"])
        before = worst([a] + e["regs_um"] + [b])
        if n == 0: rep["failed"].append((tn, e.get("conn"), round(before, 1), "no regs")); continue
        L = md(a, b)
        if before <= LIM:                  # only in-core regs: snap those to the nearest street point
            e["regs_um"] = [snap(q) if inc(q) else q for q in e["regs_um"]]
            e["note"] = e.get("note", "") + "; QUAD-7 in-core station re-sited to street"
            rep["incore_fixed"] = rep.get("incore_fixed", 0) + 1
            if worst([a] + e["regs_um"] + [b]) <= LIM: rep["fixed"] += 1; continue
        regs = []
        for j in range(1, n+1):           # even split along x-first L path
            s = L*j/(n+1); dx = abs(b[0]-a[0])
            q = [a[0] + np.sign(b[0]-a[0])*min(s, dx), a[1] + np.sign(b[1]-a[1])*max(0, s-dx)]
            regs.append(snap(q))
        for _ in range(4*n + 20):          # local relaxation of the worst hop
            pts = [a] + regs + [b]; hops = [md(u, v) for u, v in zip(pts, pts[1:])]
            k = int(np.argmax(hops))
            if hops[k] <= LIM: break
            cand = [j for j in (k-1, k) if 0 <= j < n]
            moved = False
            for j in cand:
                nq = best_between(pts[j], pts[j+2])
                old = max(md(pts[j], regs[j]), md(regs[j], pts[j+2]))
                if max(md(pts[j], nq), md(nq, pts[j+2])) < old - 1e-6:
                    regs[j] = nq; moved = True; break
            if not moved: break
        after = worst([a] + regs + [b])
        if after < before - 1e-6:
            e["regs_um"] = regs
            e["note"] = e.get("note", "") + f"; QUAD-7 relax_internal (count kept {n}): worst hop {before:.1f} -> {after:.1f}"
        if after <= LIM: rep["fixed"] += 1
        else: rep["failed"].append((tn, e.get("conn"), e.get("launch"), e.get("capture"), n, round(L, 1), round(min(after, before), 1)))
(d / "die_plan.json").write_text(json.dumps(p, indent=1) + "\n")
(d / "relax_internal_report.json").write_text(json.dumps(rep, indent=1) + "\n")
print("bad_before", rep["chains_bad_before"], "fixed", rep["fixed"], "still_failing", len(rep["failed"]))
for f in rep["failed"][:15]: print(" ", f)
