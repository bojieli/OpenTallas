#!/usr/bin/env python3
"""PATH-S81-PD5 render: the 3 re-planned lanes, PD4 (grey dashed) vs PD5 (red), with every other re-routed lane (blue),
zoomed on the NW frame row, the NE frame row and the s_0S column above gunit.
usage: render_pd5_delta.py PLAN_PD5 ROUTES_PD4 ROUTES_PD5 OUT_PNG"""
import json, sys
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
plan, r4, r5, out = sys.argv[1:5]
P = json.load(open(plan)); A = {r["lane"]: r for r in json.load(open(r4))["routes"]}; B = {r["lane"]: r for r in json.load(open(r5))["routes"]}
ra = {p["name"]: (p["origin_um"][0], p["origin_um"][1], *P["partition_types"][p["type"]]["outline_um"]) for p in P["partitions"]}
c = lambda n: (ra[n][0]+ra[n][2]/2, ra[n][1]+ra[n][3]/2)
changed = [l for l in B if B[l]["parts"] != A[l]["parts"]]
wins = [("NW frame row (fW5_p1/p2_b0 cuts)", (2500, 18000, 11800, 24745)), ("NE frame row (fE5_p1_b0 cut)", (20000, 18000, 29500, 24745)),
        ("s_0S column above gunit (s_0S_L2 h8250 cut)", (7000, 0, 16500, 12500))]
fig, axs = plt.subplots(1, 3, figsize=(27, 9.5))
for ax, (title, (x0, y0, x1, y1)) in zip(axs, wins):
    for n, (x, y, w, h) in ra.items():
        if x+w < x0 or x > x1 or y+h < y0 or y > y1: continue
        fc = "#f3d9a4" if n.startswith("svc_") else "#cfe3f7" if n.startswith("lk_") else "#e6e6e6" if n.startswith(("fW", "fE")) else "white"
        if "_pd5_" in P["partitions"][[p["name"] for p in P["partitions"]].index(n)]["type"]: fc = "#ffd0d0"
        ax.add_patch(Rectangle((x, y), w, h, fc=fc, ec="#888888", lw=0.5)); ax.text(x+w/2, y+h/2, n, fontsize=6, ha="center", va="center")
    for l, r in B.items():
        if l in changed: continue
        xs, ys = zip(*[c(n) for n in r["parts"]]); ax.plot(xs, ys, "-", color="tab:blue", lw=0.5+r["width"]/400, alpha=0.5)
    for l in changed:
        xs, ys = zip(*[c(n) for n in A[l]["parts"]]); ax.plot(xs, ys, "--", color="#555555", lw=2.5, alpha=0.8)
        xs, ys = zip(*[c(n) for n in B[l]["parts"]]); ax.plot(xs, ys, "-", color="red", lw=2.5, alpha=0.9)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect("equal"); ax.set_title(title, fontsize=11)
fig.suptitle("PATH-S81-PD5 plan delta: red = PD5 route, grey dashed = PD4 route of the same lane, blue = other re-routed lanes; pink = new per-instance frame types (%s)" % ", ".join(changed), fontsize=10)
fig.tight_layout(); fig.savefig(out, dpi=110); print("wrote", out, changed)
