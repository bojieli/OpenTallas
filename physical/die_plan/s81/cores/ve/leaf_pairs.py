#!/usr/bin/env python3
"""CORE-S81 10-23: leaf hard-core placement study (all orientations R0 here): every leaf-internal bundle (pin-group
centroid -> partner pin-group centroid, from the closed cores' pin tables), Manhattan length, and a render in the
GEOM-REVIEW8 style (all bundles).  usage: leaf_pairs.py W H 'inst=x,y;...' OUT_PREFIX"""
import json, re, sys, collections
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
PD = "physical/die_plan/s81/inputs/core_pins/%s.json"
MOD = dict(vp="ot_s81sl_vp", vn="ot_s81sl_vn", vs="ot_s81sl_vs", vsw="ot_s81sl_vsw", vq="ot_s81sl_vq",
           rxsf="dsfd_su_t_rxsf", rxsb="dsfd_su_t_rxsb", ve="ot_s81sl_ve")
SZ = dict(vp=(734.4, 864), vn=(356.4, 356.4), vs=(172.8, 172.8), vsw=(224.64, 224.64), vq=(172.8, 129.6),
          rxsf=(140.4, 140.4), rxsb=(140.4, 140.4), ve=(345.6, 345.6))
# (core, pin groups) <-> (core, pin groups): ot_s81sl_leaf connectivity (ot_s81sl_slice.sv)
B = [("vp", "hw_ hq_ hr_ n_ wl_", "vn", "hw_ hq_ hr_ n_ wl_"), ("vp", "s_", "vs", "s_"), ("vp", "x_q x_r", "vs", "x_q x_r"),
     ("vp", "x_w", "vs", "x_w"), ("vp", "m_", "vq", "m_"), ("vn", "y", "vq", "y"), ("vs", "u um_", "vq", "u um_"),
     ("ve", "r_ p_", "vs", "ve_r ve_p"), ("ve", "a_", "vs", "ve_a"), ("ve", "o_", "vs", "ve_o"),
     ("vs", "sw_v sw_d sw_w sw_lim", "vsw", "i_"), ("vsw", "o_", "vs", "sw_vi sw_ri sw_fi"),
     ("vs", "ra_v ra_x", "rxsf", "i_"), ("rxsf", "o_", "rxsb", "i_"), ("rxsb", "o_", "vs", "ra_vi ra_ri ra_fi")]


def pins(c):
    return json.load(open(PD % MOD[c]))["pins"]


def grp(c, pre, org):
    ps = [p for p in pins(c) if any(re.sub(r"\[.*", "", p["name"]).startswith(q) for q in pre.split())]
    n = len(ps)
    return n, (org[0] + sum(p["x"] for p in ps) / n, org[1] + sum(p["y"] for p in ps) / n)


def main(W, H, place, out):
    W, H = float(W), float(H)
    O = {k: tuple(map(float, v.split(","))) for k, v in (s.split("=") for s in place.split(";"))}
    rows = []
    fig, ax = plt.subplots(figsize=(12, 9.5))
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.5))
    for c, (x, y) in O.items():
        w, h = SZ[c]
        ax.add_patch(Rectangle((x, y), w, h, fc="#ffd27f" if c == "ve" else "#dde6f0", ec="k"))
        ax.text(x + w / 2, y + h / 2, "%s %gx%g" % (c, w, h), ha="center", va="center", fontsize=8)
        ps = pins(c)
        ax.scatter([x + p["x"] for p in ps], [y + p["y"] for p in ps], s=0.6, color="k")
    worst = 0
    for a, pa, b, pb in B:
        n, A = grp(a, pa, O[a])
        m, Bc = grp(b, pb, O[b])
        d = abs(A[0] - Bc[0]) + abs(A[1] - Bc[1])
        worst = max(worst, d)
        rows.append(dict(a=a, b=b, groups="%s|%s" % (pa, pb), bits=n, manhattan_um=round(d)))
        ax.annotate("", xy=Bc, xytext=A, arrowprops=dict(arrowstyle="->", lw=0.4 + n / 300,
                    color="red" if d > 405 else "green", alpha=0.7))
        ax.text((A[0] + Bc[0]) / 2, (A[1] + Bc[1]) / 2, "%d b %d um" % (n, d), fontsize=6,
                color="red" if d > 405 else "darkgreen")
    ax.set_xlim(-10, W + 10); ax.set_ylim(-10, H + 10); ax.set_aspect("equal")
    ax.set_title("leaf %gx%g: all leaf-internal bundles (centroid->centroid Manhattan; red > 405 um)" % (W, H), fontsize=9)
    fig.tight_layout(); fig.savefig(out + ".png", dpi=110)
    json.dump(dict(outline=[W, H], place=O, bundles=rows, worst_um=round(worst)), open(out + ".json", "w"), indent=1)
    for r in rows:
        print(r)


if __name__ == "__main__":
    main(*sys.argv[1:5])
