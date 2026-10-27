#!/usr/bin/env python3
"""HBM-MU-QUAD-5 whole-die render (extends COORD rg.py): partitions, hard cores, soft regions, internal stations,
ft-slot registers, die lanes (ft lane polylines, check.lane_geometry), clock (planned continuous mesh straps
nx x ny as die_clock_mesh builds it, core/partition taps), PG (M8/M9 grid pitch note + PG domains), io windows.
Highlights any station / ft register strictly inside a hard core (red X).
Usage: render_die.py TOOLS_DIE_PLAN PLAN_JSON OUT_DIR [--mesh 64x32] [zoom partitions...]"""
import sys, json
from pathlib import Path
tools, plan, out = sys.argv[1], sys.argv[2], Path(sys.argv[3]); sys.path.insert(0, tools)
args = sys.argv[4:]; nx, ny = 64, 32
if args and args[0] == "--mesh":
    nx, ny = map(int, args[1].split("x")); args = args[2:]
import schema as S, check as C
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.collections import PatchCollection, LineCollection
raw = S.load(plan); P = S.Plan(raw, Path(plan)); d = raw
W, H = d["die"]["outline_um"]; T = d["partition_types"]; parts = {p["name"]: p for p in d["partitions"]}
out.mkdir(parents=True, exist_ok=True)
cmap = plt.get_cmap("tab20"); tc = {t: cmap(i % 20) for i, t in enumerate(sorted(T))}


def rd(pn, o, s):
    a = P.to_die(pn, o); b = P.to_die(pn, (o[0] + s[0], o[1] + s[1]))
    return min(a[0], b[0]), min(a[1], b[1]), abs(b[0] - a[0]), abs(b[1] - a[1])


part_r, hard_r, soft_r, st, ft, taps, bad = [], [], [], [], [], [], []
for pn, p in parts.items():
    x0, y0, x1, y1 = P.rect(pn); t = T[p["type"]]
    part_r.append(((x0, y0, x1 - x0, y1 - y0), tc[p["type"]], pn))
    hbox = []
    for c in t.get("hard_cores", []):
        dx, dy = c.get("track_offset_um", [0, 0]); o = (c["origin_um"][0] + dx, c["origin_um"][1] + dy)
        hard_r.append(rd(pn, o, c["outline_um"])); hbox.append((o[0], o[1], o[0] + c["outline_um"][0], o[1] + c["outline_um"][1]))
    for c in t.get("contents", []):
        if "origin_um" in c and "outline_um" in c:
            soft_r.append(rd(pn, c["origin_um"], c["outline_um"]))

    def ins(q, e=0.5):
        return any(b[0] + e < q[0] < b[2] - e and b[1] + e < q[1] < b[3] - e for b in hbox)
    for s in t.get("internal_stations", []):
        for r in s.get("regs_um", []):
            st.append(P.to_die(pn, r))
            if ins(r):
                bad.append(P.to_die(pn, r))
    for f in t.get("ft_slots", []):
        for r in f.get("regs_um", []):
            ft.append(P.to_die(pn, r))
            if ins(r):
                bad.append(P.to_die(pn, r))
    for tp in t.get("clock", {}).get("taps", []):
        taps.append(P.to_die(pn, tp["xy"]))
lanes = []
for lid in P.lanes:
    try:
        g = C.lane_geometry(P, lid)
    except Exception:
        continue
    pts = g[0]
    if pts and len(pts) > 1:
        lanes += [(tuple(pts[i][:2]), tuple(pts[i + 1][:2])) for i in range(len(pts) - 1)]
mesh = [((W * i / nx, 0), (W * i / nx, H)) for i in range(nx + 1)] + [((0, H * j / ny), (W, H * j / ny)) for j in range(ny + 1)]


def draw(xl, yl, fn, label=True, fs=(22, 15)):
    fig, ax = plt.subplots(figsize=fs, dpi=110)
    for (x, y, w, h), c, n in part_r:
        ax.add_patch(Rectangle((x, y), w, h, fc=c, alpha=0.22, ec="black", lw=0.6))
        cx, cy = x + w / 2, y + h / 2
        if label and xl[0] <= cx <= xl[1] and yl[0] <= cy <= yl[1]:
            ax.text(cx, cy, f"{n}\n{parts[n]['type']} {parts[n]['orient']}", fontsize=6, ha="center", va="center", zorder=9)
    for g in d["die"]["pg"].get("domains", []):
        x0, y0, x1, y1 = g["rect_um"]; ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="none", ec="gold", lw=1.2, ls="--", zorder=2))
    ax.add_collection(LineCollection(mesh, colors="red", lw=0.25, alpha=0.35, zorder=2))
    ax.add_collection(PatchCollection([Rectangle(r[:2], *r[2:]) for r in soft_r], fc="none", ec="green", lw=0.4, zorder=3))
    ax.add_collection(PatchCollection([Rectangle(r[:2], *r[2:]) for r in hard_r], fc="dimgrey", alpha=0.55, ec="black", lw=0.3, zorder=4))
    if lanes:
        ax.add_collection(LineCollection(lanes, colors="purple", lw=0.3, alpha=0.5, zorder=5))
    for pts, c, s, z in ((st, "teal", 0.6, 5), (ft, "blue", 2, 6), (taps, "darkorange", 3, 7)):
        if pts:
            xs, ys = zip(*pts); ax.scatter(xs, ys, s=s, c=c, lw=0, zorder=z, marker="*" if c == "darkorange" else "o")
    if bad:
        xs, ys = zip(*bad); ax.scatter(xs, ys, s=30, c="red", marker="x", lw=1, zorder=10)
    for w_ in d["die"].get("io") or []:
        x0, y0, x1, y1 = w_["rect_um"]; ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="none", ec="magenta", hatch="xx", lw=1, zorder=8))
    rt = d["clock"]["spine"]["root_um"]; ax.plot([rt[0]], [rt[1]], "P", ms=10, color="crimson", zorder=9)
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, ec="black", lw=1.2))
    ax.set_xlim(*xl); ax.set_ylim(*yl); ax.set_aspect("equal")
    pg = d["die"]["pg"]["grid"][0]
    ax.set_title(f"{fn} ({Path(plan).parent.name}): grey=hard core, green=soft region, teal=internal station, blue=ft reg, purple=die lanes, "
                 f"orange*=clock tap, red grid=planned continuous clock mesh {nx}x{ny} (M8/M9), gold dashed=PG domains "
                 f"(core PG M8/M9 {pg['width_um']}um @ {pg['pitch_um']}um), red X = reg inside a hard core ({len(bad)})", fontsize=8)
    fig.tight_layout(); fig.savefig(out / f"{fn}.png"); plt.close(fig)


draw((-100, W + 100), (-100, H + 100), "die")
for pn in args:
    x0, y0, x1, y1 = P.rect(pn); m = 300; w, h = x1 - x0 + 2 * m, y1 - y0 + 2 * m
    draw((x0 - m, x1 + m), (y0 - m, y1 + m), "z_" + pn, fs=(max(8, 16 * w / max(w, h)), max(6, 16 * h / max(w, h))))
print("ok hard", len(hard_r), "soft", len(soft_r), "st", len(st), "ft", len(ft), "taps", len(taps), "lanes segs", len(lanes), "reg_in_core", len(bad))
