#!/usr/bin/env python3
"""A0-REPACK plan render: outline, hard children (pin faces marked), tile pin buses, soft-root fences, and the
dominant group->group flylines from the flyline model; old and new side by side at the same um scale."""
import json, re, sys, pathlib
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import flyline_model as FM
SZ = {"ROM": (172.8, 110.16), "LSL": (99.792, 140.4), "NODE": (47.52, 432.0)}
PINF = {"ROM": "W", "LSL": "E", "NODE": "W"}
COL = {"ROM": "#8fb3d9", "LSL": "#e6b07a", "NODE": "#a8d5a2"}

def draw(ax, p, tcl, fly=None, title=""):
    W, H = p["outline"]
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.5, ec="k"))
    for n, (x, y, o) in p["children"].items():
        k = re.sub(r"\d", "", n); w, h = SZ[k]
        ax.add_patch(Rectangle((x, y), w, h, fc=COL[k], ec="k", lw=0.6))
        f = PINF[k]
        if o in ("MY", "R180"): f = "E" if f == "W" else "W"
        px = x if f == "W" else x + w
        ax.plot([px, px], [y + 2, y + h - 2], color="r", lw=2.2)
        ax.text(x + w / 2, y + h / 2, f"{n}\n{o}", ha="center", va="center", fontsize=5)
    if tcl:
        for m in re.finditer(r"name (\w+) type (EXCLUSIVE) .*? boxes \{\{([\d. ]+)\}\}", open(tcl).read()):
            x0, y0, x1, y1 = map(float, m.group(3).split())
            ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="#c050c0", alpha=0.35, ec="#802080", lw=0.4))
            ax.text(x0, y1, m.group(1), fontsize=4, color="#601060", va="bottom")
    for b, (x, y) in p["ports"].items():
        ax.plot([x], [y], marker="s", ms=3, color="g")
        ax.text(x + (4 if x < 1 else -4), y, b[2:], fontsize=4.5, color="darkgreen", ha="left" if x < 1 else "right")
    if fly:
        for a, b, n, d in fly["edges"][:40]:
            pa = fly["pos"].get(a); pb = fly["pos"].get(b)
            if pa and pb:
                ax.plot([pa[0], pb[0]], [pa[1], pb[1]], color="b", alpha=0.35, lw=0.3 + n / 400)
        for g, (x, y) in fly["pos"].items():
            ax.plot([x], [y], "o", ms=2, color="navy"); ax.text(x, y, g, fontsize=3.5, color="navy")
    ax.set_xlim(-30, 850); ax.set_ylim(-20, 1180); ax.set_aspect("equal")
    ax.set_title(title, fontsize=7)

if __name__ == "__main__":
    import gen_repack as G, plans as PL
    cen = {"nl": json.load(open(sys.argv[1])), "nk": json.load(open(sys.argv[2]))}
    out = pathlib.Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
    root = G.ROOT
    for nk in (True, False):
        k = "nk" if nk else "nl"
        o = PL.old(nk); otcl = root / "tools/qwen_romleaf/rc14_2000/baseline/nk_rc13_regions.tcl"
        o["fixed"] = FM.fences(otcl); fo = FM.solve(cen[k], o)
        for var in ("f", "m"):
            kit = f"qfd_tile_{k}_romleaf_rp{var}"
            q = G.flyline_plan(nk, var); ntcl = root / f"tools/qwen_romleaf/repack/{kit}_regions.tcl"
            q["fixed"] = FM.fences(ntcl); fq = FM.solve(cen[k], q)
            fig, axs = plt.subplots(1, 2, figsize=(14, 10), dpi=150)
            draw(axs[0], o, otcl, fo, f"OLD rc15a {k.upper()} 820.8 x 907.2 = 0.745 mm2, model flyline {fo['bit_mm']} bit-mm")
            W, H = q["outline"]
            draw(axs[1], q, ntcl, fq, f"NEW {kit} {W} x {H} = {W*H/1e6:.3f} mm2, model flyline {fq['bit_mm']} bit-mm")
            fig.tight_layout(); fig.savefig(out / f"plan_{kit}.png"); plt.close(fig)
            print("PNG", out / f"plan_{kit}.png")
