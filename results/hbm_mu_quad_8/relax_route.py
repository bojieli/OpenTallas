#!/usr/bin/env python3
"""HBM-MU-QUAD-8: route-aware re-place of internal_stations chains with a hop > GATE (405 um, Manhattan as check._hops_ok).
COORD quad-7 ruling: (1) re-place the station sites ALONG THE ACTUAL ROUTE with the register count unchanged; (2) only where that
cannot reach the target, add ONE register to that chain (latency +1 cycle, priced by TOK-HBM, ledgered).
Route = 4-connected shortest path on an 8.64-um grid of the type outline, every hard core (track_offset applied) + 2.16 um clearance
blocked (no std cells in hard cores; check_station_in_core).  Registers are placed at equal arc length along the route and snapped to
the nearest free 4.32-um lattice point.  Endpoints (pins / face windows) are fixed.
usage: relax_route.py PLANDIR [TARGET=400] [GATE=405]  -> PLANDIR/relax_route_report.json"""
import json, sys, math
from collections import deque
from pathlib import Path
import numpy as np
d = Path(sys.argv[1]); TGT = float(sys.argv[2]) if len(sys.argv) > 2 else 400.0; GATE = float(sys.argv[3]) if len(sys.argv) > 3 else 405.0
NOADD = "--noadd" in sys.argv   # leave +1 decisions to relax_hop.py (min-hop over cores first)
G, F_G, CLEAR = 8.64, 4.32, 2.16
p = json.loads((d / "die_plan.json").read_text())
md = lambda a, b: abs(a[0]-b[0]) + abs(a[1]-b[1])
def worst(pts): return max(md(a, b) for a, b in zip(pts, pts[1:]))
rep = dict(target_um=TGT, gate_um=GATE, chains_bad_before=0, replaced_count_kept=0, added_one_reg=[], still_failing=[], per_type={})

def free_mask(t, g, off):
    W, H = t["outline_um"]
    xs = np.arange(off, W - off/2, g); ys = np.arange(off, H - off/2, g)
    ok = np.ones((len(ys), len(xs)), bool)
    for h in t.get("hard_cores", []) or []:
        x, y = h["origin_um"]; w, hh = h["outline_um"]; dx, dy = h.get("track_offset_um", [0, 0])
        mx = (xs > x+dx-CLEAR) & (xs < x+dx+w+CLEAR); my = (ys > y+dy-CLEAR) & (ys < y+dy+hh+CLEAR)
        ok[np.ix_(my, mx)] = False
    return xs, ys, ok

for tn, t in p["partition_types"].items():
    ist = t.get("internal_stations") or []
    bad = [e for e in ist if worst([e["from_um"]] + e["regs_um"] + [e["to_um"]]) > GATE + 1e-6]
    if not bad: continue
    rep["chains_bad_before"] += len(bad)
    xs, ys, ok = free_mask(t, G, G/2)
    nx, ny = len(xs), len(ys); okf = ok.ravel()
    fx, fy, fok = free_mask(t, F_G, F_G)
    FX, FY = np.meshgrid(fx, fy); FP = np.column_stack((FX[fok], FY[fok]))
    def fsnap(q):
        i = int(np.argmin(np.abs(FP[:, 0]-q[0]) + np.abs(FP[:, 1]-q[1]))); return [round(float(FP[i, 0]), 3), round(float(FP[i, 1]), 3)]
    def gsnap(q):
        ix = min(max(int(round((q[0]-xs[0])/G)), 0), nx-1); iy = min(max(int(round((q[1]-ys[0])/G)), 0), ny-1)
        if okf[iy*nx+ix]: return iy*nx+ix
        best, bi = 1e18, None                       # nearest free cell (ring search)
        for r in range(1, 60):
            for jy in range(max(iy-r, 0), min(iy+r, ny-1)+1):
                for jx in (ix-r, ix+r) if abs(jy-iy) != r else range(max(ix-r, 0), min(ix+r, nx-1)+1):
                    if 0 <= jx < nx and okf[jy*nx+jx]:
                        dd = abs(xs[jx]-q[0]) + abs(ys[jy]-q[1])
                        if dd < best: best, bi = dd, jy*nx+jx
            if bi is not None: return bi
        return None
    def route(a, b):
        s, g = gsnap(a), gsnap(b)
        if s is None or g is None: return None
        prev = {s: -1}; dq = deque([s])
        while dq:
            u = dq.popleft()
            if u == g: break
            uy, ux = divmod(u, nx)
            for v, cond in ((u-1, ux > 0), (u+1, ux < nx-1), (u-nx, uy > 0), (u+nx, uy < ny-1)):
                if cond and okf[v] and v not in prev: prev[v] = u; dq.append(v)
        if g not in prev: return None
        path = []; u = g
        while u != -1: path.append(u); u = prev[u]
        path.reverse()
        return [list(a)] + [[float(xs[u % nx]), float(ys[u // nx])] for u in path] + [list(b)]
    def place(poly, n):
        seg = [md(u, v) for u, v in zip(poly, poly[1:])]; S = sum(seg)
        regs, k, acc = [], 0, 0.0
        for j in range(1, n+1):
            s = S*j/(n+1)
            while k < len(seg)-1 and acc + seg[k] < s: acc += seg[k]; k += 1
            u, v = poly[k], poly[k+1]; f = 0 if seg[k] == 0 else (s-acc)/seg[k]
            regs.append(fsnap([u[0]+(v[0]-u[0])*f, u[1]+(v[1]-u[1])*f]))
        return regs, S
    pt = dict(bad=len(bad), kept=0, added=0, failing=0)
    for e in bad:
        a, b, n = e["from_um"], e["to_um"], len(e["regs_um"])
        before = worst([a] + e["regs_um"] + [b])
        poly = route(a, b)
        if poly is None:
            rep["still_failing"].append((tn, e["conn"], n, round(before, 1), "no route")); pt["failing"] += 1; continue
        regs, S = place(poly, n)
        after = worst([a] + regs + [b])
        if after <= TGT + 1e-6 or (after <= GATE and S/(n+1) <= TGT):
            e["regs_um"] = regs; pt["kept"] += 1; rep["replaced_count_kept"] += 1
            e["note"] += f"; QUAD-8 route re-place (count kept {n}): route {S:.0f} um, worst hop {before:.1f} -> {after:.1f}"
            continue
        regs1, _ = place(poly, n+1); after1 = worst([a] + regs1 + [b])
        if after1 <= GATE and not NOADD:
            e["regs_um"] = regs1; pt["added"] += 1
            e["note"] += f"; QUAD-8 +1 station register (COORD quad-7 ruling; {n}->{n+1}, +1 cycle, TOK-HBM priced): route {S:.0f} um, worst hop {before:.1f} -> {after1:.1f}"
            rep["added_one_reg"].append(dict(type=tn, conn=e["conn"], launch=e["launch"], capture=e["capture"], bits=e["bits"],
                                             regs_before=n, regs_after=n+1, route_um=round(S, 1), worst_before=round(before, 1), worst_after=round(after1, 1)))
        else:
            if not NOADD and min(after, after1) < before:
                e["regs_um"] = regs if after <= after1 else regs1
            rep["still_failing"].append((tn, e["conn"], n, round(S, 1), round(before, 1), round(min(after, after1), 1))); pt["failing"] += 1
    rep["per_type"][tn] = pt
    print(tn, pt, flush=True)
(d / "die_plan.json").write_text(json.dumps(p, indent=1) + "\n")
rep["added_chains"] = len(rep["added_one_reg"]); rep["added_bits_x_cycles"] = sum(x["bits"] for x in rep["added_one_reg"])
(d / "relax_route_report.json").write_text(json.dumps(rep, indent=1) + "\n")
print("bad_before", rep["chains_bad_before"], "kept", rep["replaced_count_kept"], "added", rep["added_chains"], "failing", len(rep["still_failing"]))
for f in rep["still_failing"][:20]: print(" ", f)
