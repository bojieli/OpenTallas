#!/usr/bin/env python3
"""CORE-S81 10-23: render one S81 leaf type's hard-core placement (plan dir) with ve's pins by group, the leaf bus
windows, ft slots and the leaf-internal core-to-core links (from ot_s81sl_leaf in ot_s81sl_slice.sv, bits).
    python3 render_leaf.py PLANDIR TYPE OUT.png"""
import json, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

LINKS = [("u_lf.u_ve", "u_lf.u_vs", 1123, "ve r/p (W face)"), ("u_lf.u_ve", "u_lf.u_vs", 805, "ve a/o (E face)"),
         ("u_lf.u_vp", "u_lf.u_vn", 1427, ""), ("u_lf.u_vp", "u_lf.u_vs", 1209, ""), ("u_lf.u_vs", "u_lf.u_vsw", 448, ""),
         ("u_lf.u_vs", "u_lf.u_rxsf", 66, ""), ("u_lf.u_rxsf", "u_lf.u_rxsb", 130, ""), ("u_lf.u_vs", "u_lf.u_vq", 271, ""),
         ("u_lf.u_vn", "u_lf.u_vq", 260, ""), ("u_lf.u_vp", "u_lf.u_vq", 11, "")]
GRP = [("r_", "tab:blue"), ("p_", "tab:cyan"), ("a_", "tab:red"), ("o_", "tab:orange"), ("", "k")]


def main(d, tn, out):
    P = json.load(open(d + "/die_plan.json"))
    t = P["partition_types"][tn]
    w, h = t["outline_um"]
    fig, ax = plt.subplots(figsize=(11, 9.5))
    ax.add_patch(Rectangle((0, 0), w, h, fill=False, lw=1.5))
    for b in t.get("buses", []):
        f, (a, z) = b["face"], b["window_um"]
        xy = {"N": ([a, z], [h, h]), "S": ([a, z], [0, 0]), "E": ([w, w], [a, z]), "W": ([0, 0], [a, z])}[f]
        ax.plot(*xy, lw=5, color="navy")
        ax.text(sum(xy[0]) / 2, sum(xy[1]) / 2 + 12, "%s %s %d b" % (b["name"], b["dir"], b["width"]), fontsize=7,
                ha="center", color="navy")
    for s in t.get("ft_slots", []):
        a, z = s["in_window_um"]
        m = (a + z) / 2
        if s["in_face"] in "EW":
            ax.plot([0, w], [m, m], color="0.6", lw=0.7, ls="--")
        else:
            ax.plot([m, m], [0, h], color="0.6", lw=0.7, ls="--")
    C = {}
    for c in t["hard_cores"]:
        (ox, oy), (cw, ch), (dx, dy) = c["origin_um"], c["outline_um"], c["track_offset_um"]
        x0, y0 = ox + dx, oy + dy
        C[c["inst"]] = (x0, y0, cw, ch)
        ax.add_patch(Rectangle((x0, y0), cw, ch, fc="#ffd27f" if c["module"] == "ot_s81sl_ve" else "#dde6f0",
                               ec="k", lw=1))
        ax.text(x0 + cw / 2, y0 + ch / 2, "%s\n%s\n%.0fx%.0f" % (c["inst"].split(".")[-1], c["module"], cw, ch),
                fontsize=7, ha="center", va="center")
        if c["module"] == "ot_s81sl_ve":
            pins = json.load(open(d + "/" + c["pins_file"]))["pins"]
            for pre, col in GRP:
                ps = [p for p in pins if p["name"].startswith(pre)] if pre else \
                     [p for p in pins if not any(p["name"].startswith(g) for g, _ in GRP[:-1])]
                ax.scatter([x0 + p["x"] for p in ps], [y0 + p["y"] for p in ps], s=1.5, color=col,
                           label="ve %s pins (%d)" % (pre or "other", len(ps)))
    for a, b, bits, lab in LINKS:
        if a in C and b in C:
            A, B = C[a], C[b]
            ax.annotate("", xy=(B[0] + B[2] / 2, B[1] + B[3] / 2), xytext=(A[0] + A[2] / 2, A[1] + A[3] / 2),
                        arrowprops=dict(arrowstyle="-", lw=0.5 + bits / 400, color="green", alpha=0.6))
    ax.set_xlim(-20, w + 20)
    ax.set_ylim(-20, h + 40)
    ax.set_aspect("equal")
    ax.legend(fontsize=7, loc="lower left", markerscale=6)
    ax.set_title("%s %gx%g: hard cores (CORE-S81 leaf placement + ve r5 closed view); green = core links (width ~ bits); "
                 "dashed = ft slots" % (tn, w, h), fontsize=8)
    fig.tight_layout()
    fig.savefig(out, dpi=110)


if __name__ == "__main__":
    main(*sys.argv[1:4])
