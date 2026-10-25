"""LEAF4 leaf type render: hard cores (grey), FT windows (blue N/S, green E/W), ft station sites (bit_sites_um / regs_um
dots), internal stations (red), FT corridor demand bars (need width at 16 b/um under each window).
usage: rleaf.py PLAN TYPE OUT.png [TITLE]"""
import json, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P = json.load(open(sys.argv[1])); tn = sys.argv[2]; T = P["partition_types"][tn]
W, H = T["outline_um"]
f, ax = plt.subplots(figsize=(11, 9.5))
ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.5))
for c in T["hard_cores"]:
    x, y = c["origin_um"]; w, h = c["outline_um"]
    ax.add_patch(Rectangle((x, y), w, h, fc="#bbbbbb", ec="k", lw=.6))
    ax.text(x + w / 2, y + h / 2, c["inst"].replace("u_lf.", "").replace("u_vp.g_ln", "ln").replace(".u_l", ""), fontsize=6, ha="center", va="center")
for s in T["ft_slots"]:
    for face, win in ((s["in_face"], s["in_window_um"]), (s["out_face"], s["out_window_um"])):
        a, b = win
        if face in "NS":
            y = H if face == "N" else 0
            ax.plot([a, b], [y, y], lw=5, c="tab:blue", alpha=.5)
        else:
            x = W if face == "E" else 0
            ax.plot([x, x], [a, b], lw=5, c="tab:green", alpha=.5)
    pts = []
    for k in ("bit_sites_um",):
        v = s.get(k)
        if isinstance(v, list):
            def walk(z):
                if isinstance(z, list) and len(z) == 2 and all(isinstance(q, (int, float)) for q in z): pts.append(z)
                elif isinstance(z, list):
                    for q in z: walk(q)
            walk(v)
    if not pts:
        for r in s.get("regs_um", []) or []:
            if isinstance(r, list) and len(r) == 2 and all(isinstance(q, (int, float)) for q in r): pts.append(r)
    if pts:
        pts = pts[::max(1, len(pts) // 3000)]
        ax.scatter([p[0] for p in pts], [p[1] for p in pts], s=.5, c="tab:blue", alpha=.4)
for e in T.get("internal_stations", []):
    for r in e.get("regs_um", []):
        ax.plot(r[0], r[1], "r.", ms=2)
ax.set_xlim(-20, W + 20); ax.set_ylim(-20, H + 20); ax.set_aspect("equal")
ax.set_title(sys.argv[4] if len(sys.argv) > 4 else tn, fontsize=9)
f.savefig(sys.argv[3], dpi=110, bbox_inches="tight")
