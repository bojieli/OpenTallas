#!/usr/bin/env python3
"""render old vs F3 geometry (sinks, SRAMs, entry, islands, optional tree nodes)."""
import json, sys
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
def load(geo):
    S, M, C, E = [], [], None, None
    for l in open(geo):
        f = l.split()
        if not f: continue
        if f[0] == "SINK": S.append((float(f[1]), float(f[2])))
        if f[0] == "MACRO": M.append(list(map(float, f[3:7])))
        if f[0] == "DIE": C = list(map(float, f[1:5]))
        if f[0] == "PIN" and f[1] == "ck": E = (float(f[2]), float(f[3]))
    return S, M, C, E
out = sys.argv[1]; panels = sys.argv[2:]
fig, ax = plt.subplots(1, len(panels), figsize=(5.5 * len(panels), 6))
for a, spec in zip(ax, panels):
    title, geo, isl, model = (spec.split(",") + ["", ""])[:4]
    S, M, C, E = load(geo)
    a.scatter([p[0] for p in S], [p[1] for p in S], s=0.5)
    for m in M: a.add_patch(plt.Rectangle((m[0], m[1]), m[2] - m[0], m[3] - m[1], fill=False, color="r"))
    a.add_patch(plt.Rectangle((C[0], C[1]), C[2], C[3], fill=False, color="k"))
    a.plot([E[0]], [E[1]], "k*", ms=14)
    if model:
        d = json.load(open(model))
        nd = {n: c for n, p, c, cl in d["nodes"]}
        for n, p, c, cl in d["nodes"]:
            if p in nd: a.plot([nd[p][0], c[0]], [nd[p][1], c[1]], "g-", lw=0.6)
        for n, p, c, k in d["leaves"]: a.plot([c[0]], [c[1]], "g.", ms=3)
    if isl:
        r = json.load(open(isl))
        for q in r["islands"]:
            x0, y0, x1, y1 = q["rect_um"]; a.add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, color="m"))
    a.set_title(title, fontsize=9); a.set_aspect("equal"); a.set_xlim(-2, 262); a.set_ylim(-2, 280)
plt.tight_layout(); plt.savefig(out, dpi=90)
