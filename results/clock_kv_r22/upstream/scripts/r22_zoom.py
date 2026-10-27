import json, sys, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
sys.path.insert(0, sys.argv[4]); import schema as S
rows = json.load(open(sys.argv[1])); P = S.Plan(json.load(open(sys.argv[2]))); out = sys.argv[3]
part = "hg_WS_0"; r = P.rect(part)
fig, ax = plt.subplots(figsize=(10, 9))
ax.add_patch(Rectangle((r[0], r[1]), r[2]-r[0], r[3]-r[1], fill=False, ec="k", lw=1.5))
t = P.ptype(part)
for h in t.get("hard_cores", []):
    ox, oy = h["origin_um"]; w, hh = h["outline_um"]
    a = P.to_die(part, (ox, oy)) if hasattr(P, "to_die") else (r[0]+ox, r[1]+oy)
    b = P.to_die(part, (ox+w, oy+hh)) if hasattr(P, "to_die") else (r[0]+ox+w, r[1]+oy+hh)
    x0, x1 = sorted([a[0], b[0]]); y0, y1 = sorted([a[1], b[1]])
    col = {"kv3_head_eighth_e0": "#f4c0c0", "kv3_head_eighth_e2": "#c0d8f4"}.get(h["module"], "#e0e0e0")
    ax.add_patch(Rectangle((x0, y0), x1-x0, y1-y0, fc=col, ec="gray", lw=.5))
    ax.text((x0+x1)/2, (y0+y1)/2, h["inst"], fontsize=6, ha="center")
for x in rows:
    if x["part"] != part: continue
    o, n = x["old_xy"], x["new_xy"]
    c = "red" if x["level"] == 10 else "blue"
    ax.scatter([o[0]], [o[1]], marker="x", c=c, s=50); ax.scatter([n[0]], [n[1]], marker="o", c=c, s=50)
    ax.annotate("", xy=n, xytext=o, arrowprops=dict(arrowstyle="->", color=c))
ax.set_xlim(r[0]-20, r[2]+20); ax.set_ylim(r[1]-20, r[3]+20); ax.set_aspect("equal")
ax.set_title("CLOCK-KV-R22 hg_WS_0: e0 L10 (red) / e2 L9 (blue) node buffers, x = R19 in-core island, o = R22 upstream site")
fig.tight_layout(); fig.savefig(out, dpi=110)
