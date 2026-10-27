"""R20 GEOM render: die GRT (signals + fixed clock) guide density per layer group + partitions + clock fixed wires."""
import json, sys, collections
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
guide, mesh, plan, out = sys.argv[1:5]
P = json.load(open(plan)); W, H = P["die"]["outline_um"]
G = 54.0; nx, ny = int(W // G) + 1, int(H // G) + 1
dens = {g: np.zeros((ny, nx)) for g in ("M4-M5", "M6-M7", "M8-M9")}
grp = {"M4": "M4-M5", "M5": "M4-M5", "M6": "M6-M7", "M7": "M6-M7", "M8": "M8-M9", "M9": "M8-M9"}
nets = 0
with open(guide) as f:
    for ln in f:
        t = ln.split()
        if len(t) == 5 and t[4] in grp:
            x0, y0, x1, y1 = (float(v) / 1000.0 for v in t[:4])
            i0, i1 = int(x0 // G), int(min(x1, W - 1) // G); j0, j1 = int(y0 // G), int(min(y1, H - 1) // G)
            dens[grp[t[4]]][j0:j1 + 1, i0:i1 + 1] += 1
        elif len(t) == 1 and t[0] not in ("(", ")"):
            nets += 1
M = json.load(open(mesh))
fig, ax = plt.subplots(1, 3, figsize=(30, 9))
for a, (g, d) in zip(ax, dens.items()):
    a.imshow(np.log1p(d), origin="lower", extent=[0, W, 0, H], cmap="magma")
    for p in P["partitions"]:
        ox, oy = p["origin_um"]; tw, th = P["partition_types"][p["type"]]["outline_um"]
        if p.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"):
            tw, th = th, tw
        a.add_patch(Rectangle((ox, oy), tw, th, fill=False, lw=0.3, ec="cyan"))
    if g == "M8-M9":
        for w in M["fixed_wires"]:
            for s in w["segs"]:
                a.plot([s[1], s[3]], [s[2], s[4]], lw=0.3, c="lime")
    a.set_title(f"{g} GRT guide gcell count (log) - QC plan_d43, signals+clock")
    a.set_xlim(0, W); a.set_ylim(0, H)
fig.suptitle(f"INFRA-FIRST-QC-R20 die GRT: {nets} guide nets; clock fixed wires lime (M8-M9 panel); partitions cyan")
fig.tight_layout(); fig.savefig(out, dpi=80)
# zoom on centre channel
fig, a = plt.subplots(figsize=(16, 6))
d = dens["M6-M7"]
a.imshow(np.log1p(d), origin="lower", extent=[0, W, 0, H], cmap="magma")
for w in M["fixed_wires"]:
    for s in w["segs"]:
        a.plot([s[1], s[3]], [s[2], s[4]], lw=0.8, c="lime")
a.axhline(13132.8, c="w", lw=0.5); a.axhline(13176.0, c="w", lw=0.5)
a.set_xlim(12000, 19000); a.set_ylim(12600, 13700); a.set_aspect("auto")
a.set_title("centre clock channel zoom: M6-M7 guide density + clock wires (channel edges white)")
fig.tight_layout(); fig.savefig(out.replace(".png", "_chan.png"), dpi=80)
print("nets", nets, {g: int(d.sum()) for g, d in dens.items()})
