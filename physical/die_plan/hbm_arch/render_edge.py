#!/usr/bin/env python3
"""PATH-HBM/EDGE render: the +GROW band, L156 (2740 direct) + L74 (TKM direct) windows, typed chains, old b101 path."""
import json, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
plan_dir, base_dir, out = sys.argv[1], sys.argv[2], sys.argv[3]
raw = json.load(open(plan_dir + "/die_plan.json"))
base = json.load(open(base_dir + "/die_plan.json"))
rep = json.load(open(plan_dir + "/edge_report.json"))
T = raw["partition_types"]
P = {p["name"]: p for p in raw["partitions"]}
CUT, G = rep["growth"]["cut_y_um"], rep["growth"]["growth_um"]
fig, axs = plt.subplots(1, 2, figsize=(22, 13), gridspec_kw=dict(width_ratios=[1.25, 1]))
def world(pn, xy):
    p = P[pn]; w = T[p["type"]]["outline_um"][0]
    x = xy[0] if p.get("orient", "R0") == "R0" else w - xy[0]
    return p["origin_um"][0] + x, p["origin_um"][1] + xy[1]
for ax, (x0, x1, y0, y1), ttl in ((axs[0], (11200, 15400, 4200, 10400), "NW_hub / NW_b101 / root (die frame, um)"),
                                  (axs[1], (13300, 15100, 5100, 9200), "root W channel: landings + typed chains")):
    for p in raw["partitions"]:
        o = p["origin_um"]; w, h = T[p["type"]]["outline_um"]
        if o[0] > x1 or o[0] + w < x0 or o[1] > y1 or o[1] + h < y0: continue
        fc = {"root": "#fff4e0", "q_hub_nw": "#e8f0ff", "q_b101_nw": "#ffe8e8"}.get(p["type"], "#f2f2f2")
        ax.add_patch(Rectangle(o, w, h, fc=fc, ec="k", lw=1.2))
        ax.text(max(o[0], x0) + 20, min(o[1] + h, y1) - 120, p["name"], fontsize=10, weight="bold")
        for c in T[p["type"]].get("hard_cores", []):
            cx, cy = world(p["name"], c["origin_um"]); cw, ch = c["outline_um"]
            if p.get("orient", "R0") != "R0": cx -= cw
            hl = any(k in c["inst"] for k in ("idx__ctl", "argmax", "tkm_SW_root"))
            ax.add_patch(Rectangle((cx, cy), cw, ch, fc="#c9a0dc" if hl else "#d0d0d0", ec="#666", lw=0.4))
            if hl and ax is axs[1]: ax.text(cx + 5, cy + 10, c["inst"].replace("u_", ""), fontsize=7)
    # band
    ax.add_patch(Rectangle((x0, CUT), x1 - x0, G, fc="#7fd67f", alpha=0.25, ec="g", ls="--", lw=1.5))
    ax.text(x0 + 30, CUT + G / 2, f"+{G:g} um edge band (y {CUT:g}..{CUT+G:g})", color="g", fontsize=9, va="center")
    # RX
    rx = next(c for c in T["root"]["contents"] if c["inst"] == "u_tkx_rx_SW")
    rxx, rxy = world("root", rx["origin_um"])
    ax.add_patch(Rectangle((rxx, rxy), *rx["outline_um"], fc="#ff9f1c", ec="k", lw=0.8))
    if ax is axs[1]: ax.text(rxx - 10, rxy - 60, "u_tkx_rx_SW (FIRM)", fontsize=8, color="#b35c00", ha="right")
    # windows
    for pr in raw["ports"]:
        lid = pr["id"].split("_")[0]
        if lid not in ("L74", "L156", "L13", "L89", "L4", "L4m", "L9", "L63", "L62", "L12"): continue
        if pr["face"] in "EW":
            xa = P[pr["src"]["part"]]["origin_um"][0] + (T[P[pr["src"]["part"]]["type"]]["outline_um"][0] if pr["face"] == "E" else 0)
            col = {"L74": "#d00000", "L156": "#0050ff"}.get(lid, "#555")
            ax.plot([xa, xa], pr["window_um"], color=col, lw=7 if lid in ("L74", "L156") else 3, solid_capstyle="butt")
            ax.text(xa + 15, sum(pr["window_um"]) / 2, f"{pr['id']} {pr['width']}b", fontsize=8, color=col, va="center")
    # old L74 path (base) via b101
    bp = {p["id"]: p for p in base["ports"]}
    for pid, face in (("L74_0", "S"), ("L74_1", "E")):
        pr = bp[pid]
        if face == "S":
            ax.plot(pr["window_um"], [6065.28, 6065.28], color="#d00000", lw=4, ls=":", alpha=0.6)
        else:
            ax.plot([13357.44, 13357.44], pr["window_um"], color="#d00000", lw=4, ls=":", alpha=0.6)
    for pid in ("L157_0", "L157_1"):
        pr = bp[pid]
        if pr["face"] == "S": ax.plot(pr["window_um"], [6065.28, 6065.28], color="#0050ff", lw=4, ls=":", alpha=0.5)
        else: ax.plot([13357.44, 13357.44], pr["window_um"], color="#0050ff", lw=4, ls=":", alpha=0.5)
    # chains
    for tn, pn in (("root", "root"), ("q_hub_nw", "NW_hub")):
        for e in T[tn].get("internal_stations", []):
            if e.get("conn") not in ("bus:L156_i", "bus:L156_o", "bus:L74_i", "bus:L74_o"): continue
            pts = [e["from_um"]] + e["regs_um"] + [e["to_um"]]
            W = [world(pn, q) for q in pts]
            col = "#d00000" if "L74" in e["conn"] else "#0050ff"
            ax.plot([q[0] for q in W], [q[1] for q in W], "-", color=col, lw=0.9, alpha=0.8)
            ax.plot([q[0] for q in W[1:-1]], [q[1] for q in W[1:-1]], "o", color=col, ms=2.5)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect("equal"); ax.set_title(ttl)
fig.suptitle("PATH-HBM/EDGE 10-25: +501.12 band; L156 2740b direct (blue) in band; L74 TKM 1171bx2 direct (red) low on "
             "NW_hub/root face next to RX; dotted = R1DELTA via NW_b101 (removed)", fontsize=12)
plt.tight_layout(); plt.savefig(out, dpi=110)
print("wrote", out)
