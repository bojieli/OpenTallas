#!/usr/bin/env python3
"""draw_west.py BASE MOVED OUT.png : north-west HEAD band before/after the west growth, with the fixed-face windows."""
import json, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

B, M, out = json.load(open(sys.argv[1])), json.load(open(sys.argv[2])), sys.argv[3]
X0, X1, Y0, Y1 = 0, 9400, 13800, 17560
COL = {"hd_serdes": "#9ecae1", "hd_lep0N": "#fdae6b", "hd_ctl": "#c7e9c0", "hd_ctl_n": "#c7e9c0", "hd_tile": "#dadaeb",
       "hd_turn_a": "#eeeeee", "hd_turn_b": "#eeeeee", "hd_spn_wshim_tx": "#fcbba1"}


def win_die(P, part, bus):
    t = P["partition_types"][part["type"]]
    ox, oy = part["origin_um"]
    for s in t.get("ft_slots") or []:
        for side, suf in (("in", "_i"), ("out", "_o")):
            if s["name"] + suf == bus and s[side + "_face"] == "N":
                w = s[side + "_window_um"]; return ox + w[0], ox + w[1], oy + t["outline_um"][1]
    for b in t.get("buses") or []:
        if b["name"] == bus and b.get("face") == "N":
            w = b["window_um"]; return ox + w[0], ox + w[1], oy + t["outline_um"][1]
    return None


def panel(ax, P, title, moved):
    pt = P["partition_types"]
    parts = {p["name"]: p for p in P["partitions"]}
    for p in P["partitions"]:
        x, y = p["origin_um"]; w, h = pt[p["type"]]["outline_um"]
        if x > X1 or x + w < X0 or y > Y1 or y + h < Y0: continue
        fc = COL.get(p["type"], "#fff7bc" if p["type"].startswith("hd_st") else "#f0f0f0")
        ax.add_patch(Rectangle((x, y), w, h, fc=fc, ec="red" if p["name"] in moved else "k", lw=1.6 if p["name"] in moved else 0.5))
        if w > 400:
            ax.text(x + w / 2, y + h / 2, f"{p['name']}\n{p['type']}\n{w:.0f}x{h:.0f}", ha="center", va="center", fontsize=6)
    # fixed-face windows: serdes S-face coll windows vs the station / lep N-face windows
    for po in P["ports"]:
        s, d = po["src"]["part"], po["dst"]["part"]
        for a, b in ((s, d), (d, s)):
            if parts[a]["type"] == "hd_serdes" and b in parts and parts[b]["type"] != "hd_serdes":
                end = po["dst"] if b == d else po["src"]
                wd = win_die(P, parts[b], end["bus"])
                if wd:
                    ax.plot([wd[0], wd[1]], [wd[2], wd[2]], color="blue", lw=4, solid_capstyle="butt")
                    ax.text(wd[0], wd[2] - 70, end["bus"], fontsize=5, color="blue")
    ax.axvline(8760.96, color="purple", ls="--", lw=0.8); ax.text(8780, 13850, "clock trunk x=8760.96", fontsize=6, color="purple")
    ax.set_xlim(X0, X1); ax.set_ylim(Y0, Y1); ax.set_aspect("equal"); ax.set_title(title, fontsize=9)


bp = {p["name"]: p["origin_um"] for p in B["partitions"]}
moved = {p["name"] for p in M["partitions"] if p["origin_um"] != bp[p["name"]]}
fig, axs = plt.subplots(2, 1, figsize=(16, 14))
panel(axs[0], B, "BEFORE (k1): lep0N 1892.16 wide; station chain nst1..nst4 abutted 1684.8 -> 8760.96; blue = N-face windows to the fixed SerDes", set())
panel(axs[1], M, "AFTER (west pass): lep0N 2090.88 (+198.72 W), nst1-4/nst3_* -198.72 (red); nst1 = new type hd_st_turn_nw; blue windows keep DIE x", moved)
plt.tight_layout(); plt.savefig(out, dpi=110)
print("wrote", out, "moved", sorted(moved))
