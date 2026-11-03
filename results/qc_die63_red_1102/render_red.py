#!/usr/bin/env python3
"""DIE-QC-64/RED GEOM render: su_c type frame before/after the RED event (hard cores, content halos, clock taps, reset
tap, bus windows by face; the RED core pins; the relay legs face->core and core->N-face stations with their hop length).
usage: render_red.py BASE_PLAN NEW_PLAN PINS_JSON TYPE OUT.png"""
import json
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

base_p, new_p, pins_p, T, out = sys.argv[1:6]
HL = {"x_su_l0_i": "tab:blue", "x_su_l0_p1_i": "tab:blue", "x_su_l1_i": "tab:green", "x_su_l1_p1_i": "tab:green",
      "x_ctl_o": "tab:red", "x_sc_o": "tab:purple"}


def win(t, b):
    W, H = t["outline_um"]
    lo, hi = b["window_um"]
    return {"E": ((W, lo), (W, hi)), "W": ((0, lo), (0, hi)), "N": ((lo, H), (hi, H)), "S": ((lo, 0), (hi, 0))}[b["face"]]


def draw(ax, P, title, pins=None):
    t = P["partition_types"][T]
    W, H = t["outline_um"]
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.5, ec="k"))
    for c in t["contents"]:
        if c.get("origin_um") and c.get("outline_um"):
            (x, y), (w, h) = c["origin_um"], c["outline_um"]
            ax.add_patch(Rectangle((x, y), w, h, fill=False, ls="--", lw=0.6, ec="0.5"))
    for hc in t["hard_cores"]:
        (x, y), (w, h) = hc["origin_um"], hc["outline_um"]
        red = hc["inst"] == "u_red_u_core"
        ax.add_patch(Rectangle((x, y), w, h, fc=("salmon" if red else "lightsteelblue"), ec="k", lw=0.8, alpha=0.8))
        ax.text(x + w / 2, y + h / 2, hc["inst"].replace("u_suvm_u_vm8q_", "").replace("u_suvm_", ""), ha="center",
                va="center", fontsize=6)
    for b in t["buses"]:
        (x0, y0), (x1, y1) = win(t, b)
        col = HL.get(b["name"], "0.75")
        ax.plot([x0, x1], [y0, y1], lw=(4 if b["name"] in HL else 2), color=col, solid_capstyle="butt")
    for tp in t["clock"]["taps"]:
        x, y = tp["xy"]
        ax.plot(x, y, marker=("*" if tp.get("kind") == "core" else "^"), color="orange", ms=6, mec="k", mew=0.3)
    rt = t.get("reset", {}).get("tap_um")
    if rt:
        ax.plot(*rt, marker="s", color="magenta", ms=5)
    rc = [h for h in t["hard_cores"] if h["inst"] == "u_red_u_core"]
    if rc and pins:
        ox, oy = rc[0]["origin_um"]
        fc = {"E": "tab:blue", "W": "tab:green", "S": "tab:red", "N": "k"}
        for p in pins:
            ax.plot(ox + p["x"], oy + p["y"], ".", ms=1, color=fc.get(p["face"], "k"))
        # relay legs: worst lane station -> core face pin; core S pin -> N stations (straight, labelled Manhattan length)
        bus = {b["name"]: b for b in t["buses"]}

        def mid(n):
            (x0, y0), (x1, y1) = win(t, bus[n])
            return ((x0 + x1) / 2, (y0 + y1) / 2), ((x0, y0), (x1, y1))
        legs = []
        for n, face in (("x_su_l0_i", "E"), ("x_su_l1_i", "W")):
            if n in bus:
                ends = mid(n)[1]
                cp = [p for p in pins if p["face"] == face]
                px = ox + sum(p["x"] for p in cp) / len(cp)
                py = oy + sum(p["y"] for p in cp) / len(cp)
                far = max(ends, key=lambda e: abs(e[0] - px) + abs(e[1] - py))
                legs.append((far, (px, py), 2))
        sp = [p for p in pins if p["face"] == "S" and p["bus"] in ("red_we", "red_addr", "red_data")]
        if sp:
            sx = ox + sum(p["x"] for p in sp) / len(sp)
            sy = oy
            for n in ("x_ctl_o", "x_sc_o"):
                if n in bus:
                    ends = mid(n)[1]
                    far = max(ends, key=lambda e: abs(e[0] - sx) + abs(e[1] - sy))
                    legs.append(((sx, sy), far, 3))
        for (a, b, k) in legs:
            L = abs(a[0] - b[0]) + abs(a[1] - b[1])
            ax.annotate("", xy=b, xytext=a, arrowprops=dict(arrowstyle="->", color="k", lw=0.8, ls=":"))
            ax.text((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, f"{L:.0f} um / {k} st -> {L / (k + 1):.0f} um/hop",
                    fontsize=6, bbox=dict(fc="w", ec="none", alpha=0.8))
    ax.set_xlim(-60, W + 60)
    ax.set_ylim(-60, H + 60)
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=8)


B = json.load(open(base_p))
N = json.load(open(new_p))
pins = json.load(open(pins_p))
fig, axs = plt.subplots(1, 2, figsize=(16, 9), dpi=130)
draw(axs[0], B, f"{T} BASE (main plan_qc52)")
draw(axs[1], N, f"{T} RED event: u_red_u_core 276.48^2 @ {[h for h in N['partition_types'][T]['hard_cores'] if h['inst']=='u_red_u_core'][0]['origin_um']}", pins)
fig.suptitle("blue = lane l0 in (E), green = lane l1 in (W), red = x_ctl_o, purple = x_sc_o; * core taps, ^ glue taps, "
             "magenta = reset tap; dashed = content halos", fontsize=8)
fig.tight_layout()
fig.savefig(out)
print(out)
