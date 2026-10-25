"""Render E3 placement: macros, std cells, flops, ROM->CID capture regs (g_capture_first), u_map logic, pins.
usage: python3 render_e3.py placed.csv out.png title"""
import csv, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
rows = list(csv.DictReader(open(sys.argv[1])))
fig, ax = plt.subplots(figsize=(13, 14.5), dpi=110)
W, H = 410.4, 466.56
ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.2, ec="k"))
grp = {"std": ([], [], "#9aa5b1", 0.3), "buf": ([], [], "#c9a227", 0.5), "ff": ([], [], "#2b6cb0", 0.6),
       "cap": ([], [], "#e53e3e", 2.5), "map": ([], [], "#dd6b20", 0.8), "pin": ([], [], "#2f855a", 1.0)}
nmac = ncap = nmap = 0
for r in rows:
    k, n = r["kind"], r["name"]
    x, y, w, h = (float(r[c]) for c in ("x", "y", "w", "h"))
    if k == "macro":
        nmac += 1
        ax.add_patch(Rectangle((x, y), w, h, fc="#e2e8f0", ec="#4a5568", lw=0.8))
        short = n.replace("\\", "").split(".")[-2:] if "." in n else [n]
        ax.text(x + w / 2, y + h / 2, "/".join(short)[-28:], ha="center", va="center", fontsize=6)
        continue
    if k == "tap":
        continue
    cx, cy = x + w / 2, y + h / 2
    if k == "ff" and ("g_capture_first" in n or "bank_word" in n):
        g = "cap"; ncap += 1
    elif "u_map" in n and k != "pin":
        g = "map"; nmap += 1
    else:
        g = k if k in grp else "std"
    grp[g][0].append(cx); grp[g][1].append(cy)
for g, (xs, ys, c, s) in grp.items():
    ax.scatter(xs, ys, s=s, c=c, lw=0, label=f"{g} ({len(xs)})", rasterized=True)
ax.set_xlim(-5, W + 5); ax.set_ylim(-5, H + 5); ax.set_aspect("equal")
ax.legend(loc="upper right", fontsize=8, markerscale=6)
ax.set_title(sys.argv[3] + f"\nmacros {nmac}, CPRE capture flops {ncap} (red), other u_map cells {nmap} (orange)", fontsize=10)
plt.tight_layout(); plt.savefig(sys.argv[2])
print("rendered", sys.argv[2], "cap", ncap, "map", nmap, "macros", nmac)
