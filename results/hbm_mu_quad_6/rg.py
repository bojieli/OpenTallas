import sys, json
from pathlib import Path
W_ = sys.argv[1]; sys.path.insert(0, W_ + "/tools/die_plan")
import schema as S
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.collections import PatchCollection, LineCollection
plan = sys.argv[2]; out = sys.argv[3]
raw = S.load(plan); P = S.Plan(raw, plan)
d = json.load(open(plan))
W, H = d["die"]["outline_um"]
T = d["partition_types"]; parts = {p["name"]: p for p in d["partitions"]}
def xf(p, xy):
    return P.to_die(p, xy)
def rect_die(pn, o, s):
    a = xf(pn, o); b = xf(pn, (o[0] + s[0], o[1] + s[1]))
    return min(a[0], b[0]), min(a[1], b[1]), abs(b[0] - a[0]), abs(b[1] - a[1])
cmap = plt.get_cmap("tab20")
tc = {t: cmap(i % 20) for i, t in enumerate(sorted(T))}
part_r, hard_r, soft_r, st_pts, ft_pts, taps = [], [], [], [], [], []
for pn, p in parts.items():
    x0, y0, x1, y1 = P.rect(pn); t = T[p["type"]]
    part_r.append((Rectangle((x0, y0), x1 - x0, y1 - y0), tc[p["type"]], pn))
    for c in t.get("hard_cores", []):
        hard_r.append(Rectangle(rect_die(pn, c["origin_um"], c["outline_um"])[:2], *rect_die(pn, c["origin_um"], c["outline_um"])[2:]))
    for c in t.get("contents", []):
        if "origin_um" in c and "outline_um" in c:
            soft_r.append(Rectangle(rect_die(pn, c["origin_um"], c["outline_um"])[:2], *rect_die(pn, c["origin_um"], c["outline_um"])[2:]))
    for s in t.get("internal_stations", []):
        for r in s.get("regs_um", []):
            st_pts.append(xf(pn, r))
    for f in t.get("ft_slots", []):
        for r in f.get("regs_um", []):
            ft_pts.append(xf(pn, r))
    for tp in t.get("clock", {}).get("taps", []):
        taps.append(xf(pn, tp["xy"]))
def draw(xlim, ylim, fn, label=True, fs=(22, 15)):
    fig, ax = plt.subplots(figsize=fs, dpi=110)
    for r, c, n in part_r:
        ax.add_patch(Rectangle(r.get_xy(), r.get_width(), r.get_height(), fc=c, alpha=0.25, ec="black", lw=0.6))
        cx, cy = r.get_x() + r.get_width() / 2, r.get_y() + r.get_height() / 2
        if label and xlim[0] <= cx <= xlim[1] and ylim[0] <= cy <= ylim[1]:
            ax.text(cx, cy, f"{n}\n{parts[n]['type']} {parts[n]['orient']}", fontsize=6, ha="center", va="center", zorder=9)
    ax.add_collection(PatchCollection(soft_r, fc="none", ec="green", lw=0.4, zorder=3))
    ax.add_collection(PatchCollection(hard_r, fc="dimgrey", alpha=0.55, ec="black", lw=0.3, zorder=4))
    if st_pts:
        xs, ys = zip(*st_pts); ax.scatter(xs, ys, s=0.6, c="teal", lw=0, zorder=5)
    if ft_pts:
        xs, ys = zip(*ft_pts); ax.scatter(xs, ys, s=2, c="blue", lw=0, zorder=6)
    if taps:
        xs, ys = zip(*taps); ax.scatter(xs, ys, s=3, c="darkorange", marker="*", lw=0, zorder=7)
    for w in d["die"].get("io") or []:
        x0, y0, x1, y1 = w["rect_um"]; ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="none", ec="magenta", hatch="xx", lw=1, zorder=8))
    rt = d["clock"]["spine"]["root_um"]; ax.plot([rt[0]], [rt[1]], "P", ms=10, color="crimson", zorder=9)
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, ec="black", lw=1.2))
    ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.set_aspect("equal")
    ax.set_title(f"{fn}: grey=hard core, green=soft block, teal=internal station, blue=ft station, orange=clock tap", fontsize=9)
    fig.tight_layout(); fig.savefig(f"{out}/{fn}.png"); plt.close(fig)
draw((-100, W + 100), (-100, H + 100), "die", label=True)
for pn in sys.argv[4:]:
    x0, y0, x1, y1 = P.rect(pn); m = 300
    w, h = x1 - x0 + 2 * m, y1 - y0 + 2 * m
    draw((x0 - m, x1 + m), (y0 - m, y1 + m), "z_" + pn, fs=(max(8, 16 * w / max(w, h)), max(6, 16 * h / max(w, h))))
print("ok", len(hard_r), len(soft_r), len(st_pts), len(ft_pts), len(taps))
