#!/usr/bin/env python3
"""draw_lep.py BASE NEW OUT.png : hd_lep0N type-local hard cores + landing bands, before / after the re-pack."""
import json, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

def dims(h):
    w, hh = h["outline_um"]
    return (hh, w) if h.get("orient") in ("R90", "R270", "MXR90", "MYR90") else (w, hh)

def panel(ax, P, title):
    t = P["partition_types"]["hd_lep0N"]; W, H = t["outline_um"]
    ax.add_patch(Rectangle((0, 0), W, H, fc="white", ec="k", lw=1.2))
    for k, b in t["clock"]["landing_contract"]["bands"].items():
        x0, y0, x1, y1 = b["rect_um"]
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="#c7e9c0", ec="green", lw=0.5, alpha=0.7))
        ax.text(x0, y1 + 3, k, fontsize=5, color="green")
    for h in t["hard_cores"]:
        x, y = h["origin_um"]; w, hh = dims(h)
        c = "#fbb4c4" if "g_pp" in h["inst"] else ("#80b1d3" if "g_tx" in h["inst"] else ("#fdb462" if "g_rx" in h["inst"] else "#b3de69"))
        ax.add_patch(Rectangle((x, y), w, hh, fc=c, ec="k", lw=0.3))
        if "g_pp" in h["inst"]: ax.text(x + w / 2, y + hh / 2, h["inst"].split(".")[2], ha="center", fontsize=8)
    for tp in t["clock"].get("taps", []) or []:
        ax.plot(tp["xy"][0], tp["xy"][1], "k+", ms=3)
    ax.set_xlim(-20, W + 20); ax.set_ylim(-20, H + 20); ax.set_aspect("equal"); ax.set_title(title, fontsize=9)

B, N = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
fig, axs = plt.subplots(1, 2, figsize=(18, 7))
panel(axs[0], B, "BEFORE k1 hd_lep0N 1892.16 x 1226.88: 3 tx/rx/sram rows in the 155-um centre band, ~5-um gaps")
panel(axs[1], N, "AFTER re-pack v1 (no growth): 2 tx rows abut the pairs, ~92-um logic street; rx column in the centre street; srams E strip")
fig.text(0.01, 0.01, "pink = lep pair cores, blue = tx SRAM, orange = rx SRAM, light green = landing SRAM, green boxes = landing bands, + = clock taps", fontsize=8)
plt.tight_layout(); plt.savefig(sys.argv[3], dpi=110); print("wrote", sys.argv[3])
