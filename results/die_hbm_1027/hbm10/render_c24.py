"""DIE-HBM-10 C24 render: hnx_rp3lp3h_n / _s with the 3 hnx_lane_x children, the REBAL-4 SRAMs (+4.32 halo), the parent
clock entry island, REBAL-4 in-core islands and the child face pins (by face).  usage: render_c24.py C24_DIR OUT.png"""
import json, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
D, out = sys.argv[1], sys.argv[2]
side = json.load(open(f"{D}/c24_side.json"))["core_views"]
pins = json.load(open(f"{D}/cores/hnx_lane_x__285.12x302.4__c24.json"))
fig, axs = plt.subplots(1, 2, figsize=(16, 15))
COL = dict(N="tab:red", S="tab:blue", W="tab:green", E="tab:purple")
def face(p, W, H):
    return "N" if p["y"] >= H - 1e-6 else "S" if p["y"] <= 1e-6 else "W" if p["x"] <= 1e-6 else "E"
for ax, mod in zip(axs, ("hnx_rp3lp3h_n", "hnx_rp3lp3h_s")):
    v = side[mod]; Wp, Hp = v["outline_um"]
    ax.add_patch(Rectangle((0, 0), Wp, Hp, fill=False, lw=2, ec="k"))
    ax.add_patch(Rectangle((4.32, 4.32), Wp - 8.64, Hp - 8.64, fill=False, lw=0.6, ec="gray", ls="--"))
    for s in v["parent_srams"]:
        x0, y0, x1, y1 = s["rect_um"]
        ax.add_patch(Rectangle((x0 - 4.32, y0 - 4.32), x1 - x0 + 8.64, y1 - y0 + 8.64, fc="none", ec="orange", lw=0.6, ls=":"))
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="orange", ec="darkorange", alpha=0.7))
    infra = json.load(open(f"{D}/../c24w/in/infra_hnx_{mod[-1]}.json"))
    for r in sorted({tuple(c["rect_um"]) for c in infra["cells"]}):
        ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc="gray", ec="none", alpha=0.5))
    for c in v["children"]:
        x0, y0, x1, y1 = c["rect_um"]; cw, chh = x1 - x0, y1 - y0
        ax.add_patch(Rectangle((x0, y0), cw, chh, fc="lightsteelblue", ec="navy", lw=1.5, alpha=0.6))
        ax.text(x0 + cw / 2, y0 + chh / 2 + 25, f"{c['inst']}\nhnx_lane_x {c['orient']}\n{cw:.2f}x{chh:.2f}",
                ha="center", va="center", fontsize=10)
        for p in pins:
            px, py = p["x"], p["y"]
            if c["orient"] == "MY": px = cw - px
            f = face(p, cw, chh) if p["name"] != "clk" else "C"
            if f == "C":
                ax.plot(x0 + px, y0 + py, marker="*", ms=12, color="k")
                continue
            if c["orient"] == "MY" and f in "WE": f = "E" if f == "W" else "W"  # mirrored face for display only
            fo = face(p, cw, chh)
            ax.plot(x0 + px, y0 + py, ".", ms=1.5, color=COL[fo])
    for xy, isl in v["parent_clock_entry"]:
        ax.add_patch(Rectangle((isl[0], isl[1]), isl[2] - isl[0], isl[3] - isl[1], fc="red", ec="red"))
        ax.annotate("parent clock entry", (xy[0], xy[1]), (xy[0] + 40, xy[1] - 60), fontsize=9, color="red",
                    arrowprops=dict(arrowstyle="->", color="red"))
    ax.set_xlim(-10, Wp + 10); ax.set_ylim(-10, Hp + 10); ax.set_aspect("equal")
    ax.set_title(f"C24 {mod} {Wp}x{Hp}: 3 x hnx_lane_x, 12 SRAM (+4.32 halo), islands (gray)\n"
                 "pins: N operands red, S ixb_p blue, W side store green, E gather/resets purple, * clk", fontsize=10)
fig.tight_layout(); fig.savefig(out, dpi=80)
print("wrote", out)
