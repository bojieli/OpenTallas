"""DIE-HBM-10 hubplace render: hub outline, 4x3 grid, placed hard cores (plan rect moved by the cell delta), faces by net ratio."""
import json, sys, re
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
d = json.load(open(sys.argv[1])); out = sys.argv[2]; nx, ny = map(int, d["grid"].split("x"))
UNIT = [("hb_coll", "COLL"), ("hcollg", "COLL"), ("cij", "COLL"), ("cxij", "COLL"), ("cxrc", "SU"), ("sucore", "SU"), ("pgp", "SU"), ("sfu", "SU"),
        ("svg", "SM"), ("smw", "SM"), ("xl_", "SM"), ("xq_", "SM"), ("wbk", "SM"), ("dbk", "DMA"), ("hb_idx", "IDX"), ("mu_", "FUSED"), ("quant", "FUSED"),
        ("hc_", "HC"), ("vmb", "VM"), ("vmks", "VM"), ("vmdel", "VM"), ("vms", "VM"), ("vmfc", "VM"), ("calendar", "VM"), ("ctl_Q", "VM")]
COL = dict(COLL="#8c6bb1", SU="#e6550d", SM="#3182bd", DMA="#636363", IDX="#31a354", FUSED="#fdae6b", HC="#9ecae1", VM="#e7ba52", UNK="#cccccc")
def unit(n):
    for k, u in UNIT:
        if k in n: return u
    return "UNK"
fig, axs = plt.subplots(1, len(d["types"]), figsize=(11 * len(d["types"]), 7))
for ax, (tn, r) in zip(axs, d["types"].items()):
    W, H = r["outline_um"]; cw, ch = W / nx, H / ny; S = r["A+B_net"]
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=2))
    for k in range(1, nx): ax.axvline(k * cw, color="k", ls="--", lw=0.8)
    for k in range(1, ny): ax.axhline(k * ch, color="k", ls="--", lw=0.8)
    for h, rc in r["hrect"].items():
        c = S["place"].get("H/" + h)
        if c is None: continue
        c0 = (min(nx - 1, max(0, int((rc[0] + rc[2]) / 2 / cw))), min(ny - 1, max(0, int((rc[1] + rc[3]) / 2 / ch))))
        dx, dy = (c[0] - c0[0]) * cw, (c[1] - c0[1]) * ch
        ax.add_patch(Rectangle((rc[0] + dx, rc[1] + dy), rc[2] - rc[0], rc[3] - rc[1], fc=COL[unit(h)], ec="k", lw=0.3, alpha=0.8))
    for f in S["all_faces"]:
        o, x, y = f["face"][0], int(f["face"][1]), int(f["face"][2]); q = f["ratio_net"]
        col = "red" if q > 1.0 else ("orange" if q > 0.9 else "green")
        if o == "v": X, Y = (x + 1) * cw, (y + 0.5) * ch; ax.plot([X, X], [y * ch, (y + 1) * ch], color=col, lw=4, alpha=0.6)
        else: X, Y = (x + 0.5) * cw, (y + 1) * ch; ax.plot([x * cw, (x + 1) * cw], [Y, Y], color=col, lw=4, alpha=0.6)
        ax.text(X, Y, f"{q:.2f}", ha="center", va="center", fontsize=9, bbox=dict(fc="white", alpha=0.8, lw=0))
    cuts = " ".join(f"{k} {v['bits']/v['net_pins']:.2f}" for k, v in S["vertical_cuts"].items())
    ax.set_title(f"{tn} {sys.argv[3] if len(sys.argv) > 3 else ""}: worst face {S['worst_ratio_net']} over {S['faces_over_net']}  cuts {cuts}  hutil {S['max_cell_hard_util']}", fontsize=10)
    ax.set_xlim(-50, W + 50); ax.set_ylim(-50, H + 50); ax.set_aspect("equal")
for u, c in COL.items(): axs[0].plot([], [], "s", color=c, label=u)
axs[0].legend(loc="upper left", fontsize=7, ncol=9)
plt.tight_layout(); plt.savefig(out, dpi=90)
