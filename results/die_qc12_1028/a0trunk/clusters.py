#!/usr/bin/env python3
"""DIE-QC-12 A0 parent local trunk, step 1: glue-register leaf clusters (<= MAXD um box) + one root INV site each.
usage: clusters.py sinks_<t>.txt out.json [maxd]"""
import json, sys, numpy as np
src, out = sys.argv[1], sys.argv[2]; MAXD = float(sys.argv[3]) if len(sys.argv) > 3 else 200.0
regs, kids, macros = [], [], []
for l in open(src):
    p = l.split()
    if p[0] == "SINK":
        x, y = int(p[4]) / 1000, int(p[5]) / 1000
        (kids if p[2].startswith("ot_qwen") else regs).append((p[1], p[2], x, y))
    elif p[0] == "MACRO":
        macros.append([int(v) / 1000 for v in p[3:7]])
    elif p[0] == "DIE":
        W, H = int(p[3]) / 1000, int(p[4]) / 1000
P = np.array([[r[2], r[3]] for r in regs])
def split(idx):
    q = P[idx]; ext = q.max(0) - q.min(0)
    lo, hi = q.min(0), q.max(0)
    ov = any(min(hi[0], m[2]) - max(lo[0], m[0]) > 10 and min(hi[1], m[3]) - max(lo[1], m[1]) > 10 for m in macros)
    if ext.max() <= MAXD and len(idx) <= 1200 and not ov: return [idx]
    if ext.max() <= 20: return [idx]
    ax = int(np.argmax(ext)); med = np.median(q[:, ax])
    if ov:
        v = np.sort(q[:, ax]); g = np.diff(v); k = int(np.argmax(g))
        if g[k] > 5: med = (v[k] + v[k + 1]) / 2
    a, b = idx[q[:, ax] <= med], idx[q[:, ax] > med]
    if len(a) == 0 or len(b) == 0: return [idx]
    return split(a) + split(b)
cl = split(np.arange(len(P)))
def boxov(idx):
    q = P[idx]; lo, hi = q.min(0), q.max(0)
    return (hi - lo).max(), any(min(hi[0], m[2]) - max(lo[0], m[0]) > 10 and min(hi[1], m[3]) - max(lo[1], m[1]) > 10 for m in macros)
changed = True
while changed:     # merge small clusters (< 60 regs) into the nearest neighbour when the union stays <= MAXD and macro-free
    changed = False
    cl.sort(key=len)
    for i, a in enumerate(cl):
        if len(a) >= 60: break
        ca = np.median(P[a], 0); best = None
        for j, b in enumerate(cl):
            if j == i: continue
            u = np.concatenate([a, b]); ext, ov = boxov(u)
            if ext <= MAXD and not ov and len(u) <= 1200:
                d = np.abs(np.median(P[b], 0) - ca).sum()
                if best is None or d < best[0]: best = (d, j, u)
        if best:
            cl = [c for k, c in enumerate(cl) if k not in (i, best[1])] + [best[2]]; changed = True; break
def inmac(x, y, h=1.0):
    return any(m[0] - h < x < m[2] + h and m[1] - h < y < m[3] + h for m in macros)
def legal(x, y):
    """nearest point outside every macro (+1 um), inside the core (5.4 um ring)"""
    x = min(max(x, 6.0), W - 6.0); y = min(max(y, 6.0), H - 6.0)
    if not inmac(x, y): return x, y
    best = None
    for m in macros:
        if m[0] - 1 < x < m[2] + 1 and m[1] - 1 < y < m[3] + 1:
            for c in ((m[0] - 1.5, y), (m[2] + 1.5, y), (x, m[1] - 1.5), (x, m[3] + 1.5)):
                if 6 <= c[0] <= W - 6 and 6 <= c[1] <= H - 6 and not inmac(*c):
                    d = abs(c[0] - x) + abs(c[1] - y)
                    if best is None or d < best[0]: best = (d, c)
    return best[1]
res = []
for i, idx in enumerate(cl):
    q = P[idx]; c = np.median(q, 0)
    rx, ry = legal(float(c[0]), float(c[1]))
    res.append(dict(name=f"a0cl{i}", n=int(len(idx)), root=[round(rx, 3), round(ry, 3)],
                    box=[round(float(v), 2) for v in (*q.min(0), *q.max(0))], regs=[regs[j][0] for j in idx]))
json.dump(dict(W=W, H=H, macros=macros, kids=[dict(inst=k[0], module=k[1], pin=[k[2], k[3]]) for k in kids], clusters=res),
          open(out, "w"))
for r in res: print(r["name"], r["n"], r["root"], r["box"])
print("clusters", len(res), "regs", len(P), "kids", len(kids))
