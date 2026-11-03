#!/usr/bin/env python3
"""DIE-KV-61/grt: whole-die GRT guide density render (signal M4-M7 / clock M8-M9 guide length per 100 um bin) with plan
partition outlines and die clock taps.  usage: render_guide.py GUIDE PLAN TREE OUT.png TITLE"""
import json, sys, re
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
sys.path.insert(0, sys.argv[6] if len(sys.argv) > 6 else ".")
G, PL, TR, OUT, TITLE = sys.argv[1:6]
P = json.load(open(PL)); W, H = 11076.48, 27043.2; BIN = 100.0
nx, ny = int(W // BIN) + 1, int(H // BIN) + 1
sig = np.zeros((ny, nx)); clk = np.zeros((ny, nx))
net = None
for ln in open(G):
    s = ln.split()
    if len(s) != 5:
        if len(s) == 1 and s[0] not in "()": net = s[0]
        continue
    L = s[4]
    if L not in ("M4", "M5", "M6", "M7", "M8", "M9"): continue
    x0, y0, x1, y1 = (int(v) / 1000.0 for v in s[:4])
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    ln_um = max(x1 - x0, y1 - y0)
    a = clk if net.startswith("ck_") or L in ("M8", "M9") else sig
    a[min(int(cy // BIN), ny - 1), min(int(cx // BIN), nx - 1)] += ln_um
import schema as S
SP = S.Plan(P)
fig, axs = plt.subplots(1, 2, figsize=(14, 17))
T = json.load(open(TR))
for ax, a, lab in ((axs[0], sig, "signal guides M4-M7 (um per 100 um bin)"), (axs[1], clk, "clock guides M8-M9 + ck_ nets")):
    im = ax.imshow(np.log10(a + 1), origin="lower", extent=(0, nx * BIN, 0, ny * BIN), cmap="magma")
    for n, p in SP.parts.items():
        t = SP.types[p["type"]]; w, h = t["outline_um"]
        o = p["origin_um"]; r = p.get("orient", "R0")
        if r in ("R90", "R270", "MXR90", "MYR90"): w, h = h, w
        ax.add_patch(Rectangle(o, w, h, fill=False, ec="cyan", lw=0.4))
    if ax is axs[1]:
        xs = [t["xy"][0] for t in T["taps"]]; ys = [t["xy"][1] for t in T["taps"]]
        ax.plot(xs, ys, "w.", ms=1)
    ax.set_title(lab, fontsize=9); ax.set_xlim(0, W); ax.set_ylim(0, H); fig.colorbar(im, ax=ax, shrink=0.4, label="log10(um+1)")
fig.suptitle(TITLE, fontsize=10); fig.tight_layout(); fig.savefig(OUT, dpi=110)
print("sig total um", round(sig.sum()), "clk total um", round(clk.sum()), "max sig bin", round(sig.max()), "max clk bin", round(clk.max()))
