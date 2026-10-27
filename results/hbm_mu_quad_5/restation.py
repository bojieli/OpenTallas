#!/usr/bin/env python3
"""HBM-MU-QUAD-5 restation (COORD GEOM planU4f B1+B2): move every internal_stations / ft_slots register point that lies
inside a hard-core outline (OBS M1-M5, no std cells) onto the nearest legal street point outside all hard cores of the
type.  Register COUNT and ORDER are unchanged (no cycle change); every hop prev->reg->next stays <= REACH Manhattan
(or <= the hop it already had, if that was longer); the chosen point minimises the added path length plus 0.25 x the
displacement, with CLEAR um clearance to every core and to the partition outline.  ft_slots bit_sites_um (the real
per-bit cell sites) are already outside cores on planU4f and are left as they are; only the nominal stage point moves.
Inside test = gchk.py (0.5 um margin, track_offset applied).  Blockers (no legal point within reach) are reported,
never forced.  Usage: restation.py IN_PLAN_DIR OUT_PLAN_DIR [--report R.json] [--reach 405] [--clear 2.16]"""
import argparse, json, shutil, collections
from pathlib import Path
import numpy as np

ap = argparse.ArgumentParser(); ap.add_argument("inp"); ap.add_argument("out"); ap.add_argument("--report")
ap.add_argument("--reach", type=float, default=405.0); ap.add_argument("--clear", type=float, default=2.16)
ap.add_argument("--step", type=float, default=0.54)
a = ap.parse_args()
inp, out = Path(a.inp), Path(a.out)
if out.exists(): shutil.rmtree(out)
shutil.copytree(inp, out, symlinks=True)
P = json.loads((out / "die_plan.json").read_text()); T = P["partition_types"]

def box(c):
    x, y = c["origin_um"]; w, h = c["outline_um"]; dx, dy = c.get("track_offset_um", [0.0, 0.0])
    return (x + dx, y + dy, x + dx + w, y + dy + h)
def inside(p, r, e=0.5): return r[0] + e < p[0] < r[2] - e and r[1] + e < p[1] < r[3] - e
md = lambda p, q: abs(p[0] - q[0]) + abs(p[1] - q[1])
def face_pt(t, face, win):
    W, H = t["outline_um"]; m = 0.5 * (win[0] + win[1])
    return dict(N=(m, H), S=(m, 0.0), E=(W, m), W=(0.0, m))[face]

def place(p, prev, nxt, B, W, H):
    """nearest legal point (cost = added length + 0.25 displacement); None if none within reach."""
    lim_a = max(a.reach, md(prev, p)) if prev is not None else None
    lim_b = max(a.reach, md(p, nxt)) if nxt is not None else None
    base = (md(prev, p) if prev is not None else 0) + (md(p, nxt) if nxt is not None else 0)
    c = a.clear
    for r in (60.0, 200.0, 450.0, 900.0):
        st = a.step if r <= 60 else 2.16
        xs = np.arange(max(c, p[0] - r), min(W - c, p[0] + r) + 1e-9, st)
        ys = np.arange(max(c, p[1] - r), min(H - c, p[1] + r) + 1e-9, st)
        if not len(xs) or not len(ys): continue
        X, Y = np.meshgrid(xs, ys); X = X.ravel(); Y = Y.ravel()
        ok = np.ones(X.shape, bool)
        for (x0, y0, x1, y1) in B:
            if x1 + c < p[0] - r or x0 - c > p[0] + r or y1 + c < p[1] - r or y0 - c > p[1] + r: continue
            ok &= ~((X > x0 - c) & (X < x1 + c) & (Y > y0 - c) & (Y < y1 + c))
        cost = 0.25 * (np.abs(X - p[0]) + np.abs(Y - p[1]))
        if prev is not None:
            da = np.abs(X - prev[0]) + np.abs(Y - prev[1]); ok &= da <= lim_a + 1e-6; cost = cost + da
        if nxt is not None:
            db = np.abs(X - nxt[0]) + np.abs(Y - nxt[1]); ok &= db <= lim_b + 1e-6; cost = cost + db
        if ok.any():
            i = int(np.argmin(np.where(ok, cost, np.inf)))
            return [round(float(X[i]), 4), round(float(Y[i]), 4)], float(cost[i]) - base
    return None, None


from collections import deque
def free_grid(B, W, H, g):
    nx, ny = int(W // g) + 1, int(H // g) + 1
    xs = (np.arange(nx) + 0.5) * g; ys = (np.arange(ny) + 0.5) * g
    X, Y = np.meshgrid(xs, ys, indexing="ij"); ok = (X > a.clear) & (X < W - a.clear) & (Y > a.clear) & (Y < H - a.clear)
    c = a.clear
    for (x0, y0, x1, y1) in B:
        ok &= ~((X > x0 - c) & (X < x1 + c) & (Y > y0 - c) & (Y < y1 + c))
    return ok, xs, ys
def snap(ok, xs, ys, p):
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    d = np.abs(X - p[0]) + np.abs(Y - p[1]); d = np.where(ok, d, np.inf)
    k = int(np.argmin(d))
    if not np.isfinite(d.ravel()[k]): return None
    return divmod(k, ok.shape[1])
def bfs_path(ok, xs, ys, A, Bp):
    s = snap(ok, xs, ys, A); t = snap(ok, xs, ys, Bp)
    if s is None or t is None: return None
    nx, ny = ok.shape; prev = -np.ones(nx * ny, np.int64); seen = np.zeros(nx * ny, bool)
    si = s[0] * ny + s[1]; ti = t[0] * ny + t[1]; seen[si] = True; q = deque([si]); okf = ok.ravel()
    while q:
        u = q.popleft()
        if u == ti: break
        i, j = divmod(u, ny)
        for v in ((u - ny) if i > 0 else -1, (u + ny) if i < nx - 1 else -1, (u - 1) if j > 0 else -1, (u + 1) if j < ny - 1 else -1):
            if v >= 0 and okf[v] and not seen[v]:
                seen[v] = True; prev[v] = u; q.append(v)
    if not seen[ti]: return None
    path = [ti]
    while path[-1] != si: path.append(int(prev[path[-1]]))
    path.reverse()
    return [(float(xs[u // ny]), float(ys[u % ny])) for u in path]
def reroute(pts, lo, hi, ok, xs, ys):
    """re-place regs pts[lo..hi] (anchors pts[lo-1], pts[hi+1]) evenly by arc length along a free shortest path."""
    A, Bp = pts[lo - 1], pts[hi + 1]
    path = bfs_path(ok, xs, ys, A, Bp)
    if path is None: return None
    full = [A] + path + [Bp]
    cum = [0.0]
    for i in range(1, len(full)): cum.append(cum[-1] + md(full[i - 1], full[i]))
    k = hi - lo + 1; L = cum[-1]; newp = []
    for m in range(1, k + 1):
        target = L * m / (k + 1)
        i = max(1, min(len(full) - 2, int(np.searchsorted(cum, target))))
        newp.append([round(full[i][0], 4), round(full[i][1], 4)])
    trial = pts[:lo] + [tuple(q) for q in newp] + pts[hi + 1:]
    hops = [md(trial[i], trial[i + 1]) for i in range(lo - 1, hi + 1)]
    return newp, max(hops)

rep = dict(moved=collections.Counter(), blockers=[], rows=[], max_hop_before=0.0, max_hop_after=0.0)
used = {p_["type"] for p_ in P["partitions"]}
for tn in sorted(used):
    t = T[tn]; B = [box(c) for c in t.get("hard_cores", [])]
    if not B: continue
    W, H = t["outline_um"]
    grid = None
    chains = []
    for e in t.get("internal_stations", []):
        if e.get("regs_um"):
            chains.append(("B1", e.get("conn"), e["regs_um"], tuple(e["from_um"]) if e.get("from_um") else None,
                           tuple(e["to_um"]) if e.get("to_um") else None))
    for s in t.get("ft_slots", []):
        if s.get("regs_um"):
            a0 = face_pt(t, s["in_face"], s["in_window_um"]) if s.get("in_window_um") else None
            b0 = face_pt(t, s["out_face"], s["out_window_um"]) if s.get("out_window_um") else None
            chains.append(("B2", s["name"], s["regs_um"], a0, b0))
    for kind, nm, regs, a0, b0 in chains:
        bad = [j for j, q in enumerate(regs) if any(inside(q, r) for r in B)]
        if not bad: continue
        pts = [a0] + [tuple(q) for q in regs] + [b0]
        hops = [md(pts[i], pts[i + 1]) for i in range(len(pts) - 1) if pts[i] is not None and pts[i + 1] is not None]
        hb = max(hops) if hops else 0.0
        pend = []
        for j in bad:
            old = list(regs[j]); prev = pts[j]; nxt = pts[j + 2]
            new, dl = place(tuple(old), prev, nxt, B, W, H)
            if new is None:
                pend.append(j); continue
            regs[j] = new; pts[j + 1] = tuple(new); rep["moved"][f"{kind}:{tn}"] += 1
            rep["rows"].append(dict(type=tn, kind=kind, conn=nm, reg=j, old=old, new=new, added_um=round(dl, 3)))
        if pend:
            if grid is None: grid = free_grid(B, W, H, 4.32)
            ok_, xs_, ys_ = grid
            lo, hi = min(pend) + 1, max(pend) + 1      # pts indices of the blocked run
            done = False
            while True:
                if pts[lo - 1] is None or pts[hi + 1] is None: break
                r_ = reroute(pts, lo, hi, ok_, xs_, ys_)
                if r_ and r_[1] <= a.reach + 1e-6:
                    for m, q in enumerate(r_[0]):
                        jj = lo - 1 + m; oldq = list(regs[jj]); regs[jj] = q; pts[jj + 1] = tuple(q)
                        rep["moved"][f"{kind}:{tn}"] += 1
                        rep["rows"].append(dict(type=tn, kind=kind, conn=nm, reg=jj, old=oldq, new=q, added_um=None, chain=[lo - 1, hi - 1]))
                    done = True; break
                if lo <= 1 and hi >= len(pts) - 2: break
                lo = max(1, lo - 1); hi = min(len(pts) - 2, hi + 1)
            if not done:
                for j in pend:
                    rep["blockers"].append(dict(type=tn, kind=kind, conn=nm, reg=j, xy=list(regs[j]),
                                                why="no free path with this register count within reach"))
        hops = [md(pts[i], pts[i + 1]) for i in range(len(pts) - 1) if pts[i] is not None and pts[i + 1] is not None]
        ha = max(hops) if hops else 0.0
        rep["max_hop_before"] = max(rep["max_hop_before"], hb); rep["max_hop_after"] = max(rep["max_hop_after"], ha)
        if ha > a.reach + 1e-6 and ha > hb + 1e-6:
            rep["blockers"].append(dict(type=tn, kind=kind, conn=nm, why=f"hop grew {hb:.1f}->{ha:.1f}"))
    for e in t.get("internal_stations", []):
        if any(r["type"] == tn and r["kind"] == "B1" and r["conn"] == e.get("conn") for r in rep["rows"]):
            e["note"] = (e.get("note", "") + " | HBM-MU-QUAD-5 restation: register(s) moved out of hard cores, count kept").strip(" |")
(out / "die_plan.json").write_text(json.dumps(P, indent=1) + "\n")
left = sum(1 for tn in used for t in [T[tn]] for B in [[box(c) for c in t.get("hard_cores", [])]]
           for coll in (t.get("internal_stations", []), t.get("ft_slots", [])) for e in coll for q in e.get("regs_um", []) or []
           if any(inside(q, r) for r in B))
rep["left_inside"] = left; rep["moved"] = dict(rep["moved"])
print(json.dumps({k: v for k, v in rep.items() if k != "rows"}, indent=1))
if a.report: Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
