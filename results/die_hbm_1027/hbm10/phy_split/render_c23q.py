"""DIE-HBM-10 C23q: zoom render of the PHY_N split area (partitions, slice macros = io rects, clk/rst taps, PHY-family
windows on the abutting faces: mcb E faces + column ports, and the per-bit ft sites of the PHY-family slots).
usage: render_c23q.py PLAN OUT_PNG"""
import json, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P = json.load(open(sys.argv[1])); T = P["partition_types"]
X0, X1, Y0, Y1 = 4600, 23800, 12000, 18700
fig, ax = plt.subplots(figsize=(22, 8.5), dpi=130)
FAM = ("L8", "L21", "L63w", "L114w", "L9", "L22", "L63", "L114")
COL = {"L8": "tab:blue", "L21": "tab:green", "L63w": "tab:orange", "L114w": "tab:red", "L9": "tab:blue", "L22": "tab:green", "L63": "tab:orange", "L114": "tab:red"}
def fam(n):
    b = n.split("x")[0].split("_")[0]
    b = b[:-1] if b.endswith("m") and b[:-1] in FAM else b
    return b if b in FAM else None
for p in P["partitions"]:
    t = T[p["type"]]; w, h = t["outline_um"]; x, y = p["origin_um"]
    if x > X1 or x + w < X0 or y > Y1 or y + h < Y0: continue
    phy = p["name"].startswith("PHY_N")
    ax.add_patch(Rectangle((x, y), w, h, fill=phy, fc=("#f3e6ff" if phy else None), ec="k", lw=1.6 if phy else 0.7))
    ax.text(x + w / 2, y + h / 2, p["name"], ha="center", va="center", fontsize=9, weight="bold" if phy else None)
    mir = p.get("orient") == "MY"
    for s in t.get("ft_slots", []):
        f_ = fam(s["name"])
        if not f_: continue
        for (bx, by) in (s.get("bit_sites_flat_um") or []):
            pass
        for st in (s.get("bit_sites_um") or []):
            xs = [(x + (w - q[0] if mir else q[0])) for q in st]; ys = [y + q[1] for q in st]
            ax.scatter(xs[::8], ys[::8], s=0.3, c=COL[f_], alpha=0.5)
        for io_ in ("in", "out"):
            if (io_ + "_window_um") not in s: continue
            a, b = s[io_ + "_window_um"]; f = s[io_ + "_face"]
            if f in "NS":
                xa, xb = (x + w - b, x + w - a) if mir else (x + a, x + b); yy = y + (h if f == "N" else 0)
                ax.plot([xa, xb], [yy, yy], c=COL[f_], lw=5, solid_capstyle="butt")
            else:
                ff = {"E": "W", "W": "E"}[f] if mir else f; xx = x + (w if ff == "E" else 0)
                ax.plot([xx, xx], [y + a, y + b], c=COL[f_], lw=5, solid_capstyle="butt")
    if phy:
        for k, m in (("clock", "^"), ("reset", "v")):
            tx, ty = t[k]["tap_um"]; ax.plot(x + tx, y + ty, m, ms=11, c="crimson" if k == "clock" else "navy")
for io in P["die"]["io"]:
    if str(io.get("part", "")).startswith("PHY_N"):
        a, b, c, d = io["rect_um"]; ax.add_patch(Rectangle((a, b), c - a, d - b, fill=False, ec="purple", lw=1.2, ls="--"))
        ax.text((a + c) / 2, d - 150, io["name"].replace("io_", "").replace("_u_phy_Q", "") + " macro", ha="center", fontsize=8, color="purple")
for q in P["ports"]:
    f_ = fam(q["id"])
    if not f_ or "window_um" not in q or q.get("face") not in ("N", "S"): continue
    a, b = q["window_um"]; src = next(p for p in P["partitions"] if p["name"] == q["src"]["part"])
    sh = T[src["type"]]["outline_um"][1]; yy = src["origin_um"][1] + (sh if q["face"] == "N" else 0)
    if Y0 < yy < Y1: ax.plot([a, b], [yy, yy], c=COL[f_], lw=7, solid_capstyle="butt")
for k, c in COL.items():
    ax.plot([], [], c=c, lw=5, label={"L8": "data in (L8 / L9)", "L21": "rdata (L21 / L22)", "L63w": "ctl in (L63w / L63)", "L114w": "rvalid (L114w / L114)"}[k])
    if k == "L114w": break
ax.plot([], [], "^", c="crimson", label="slice clk tap"); ax.plot([], [], "v", c="navy", label="slice rst tap")
ax.legend(loc="lower left", fontsize=8); ax.set_xlim(X0, X1); ax.set_ylim(Y0, Y1); ax.set_aspect("equal")
ax.set_title("C23q PHY_N split: PHY_NW PC0-9 | PHY_NC PC10-21 | PHY_NE PC22-31 (die um; windows coloured by kind, dots = ft bit sites 1/8)")
plt.tight_layout(); plt.savefig(sys.argv[2])
