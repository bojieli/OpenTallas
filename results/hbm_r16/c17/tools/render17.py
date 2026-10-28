#!/usr/bin/env python3
"""HBM-R16/C17 render: q_hub_nw / q_hub_ne hard cores (C16r vs C17g): re-oriented cores (orange), cores with G0C away
ports left (red outline), pins of re-pinned/re-spread groups in the type frame (blue = moved, grey = unchanged), and
two zooms. usage: render17.py BASIS C17G cf_rows_c17g.json OUT.png"""
import sys, json, re, collections
from pathlib import Path
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
b, g = Path(sys.argv[1]), Path(sys.argv[2]); rows = json.load(open(sys.argv[3])); outp = sys.argv[4]
B = json.loads((b / "die_plan.json").read_text())["partition_types"]; G = json.loads((g / "die_plan.json").read_text())["partition_types"]
def pname(p): return p.get("name") or (p["bus"] + ("" if p.get("bit") is None else f"[{p['bit']}]"))
def gb(n): return re.sub(r"\[\d+\]$", "", n)
cache = {}
def pins(d, f):
    k = (str(d), f)
    if k not in cache:
        js = json.loads((d / f).read_text()); cache[k] = js.get("pins", js) if isinstance(js, dict) else js
    return cache[k]
def tf(h, x, y):
    cw, ch = h["outline_um"]; o = h.get("orient", "R0"); dx, dy = h.get("track_offset_um", [0, 0])
    if o in ("MY", "R180"): x = cw - x
    if o in ("MX", "R180"): y = ch - y
    return h["origin_um"][0] + dx + x, h["origin_um"][1] + dy + y
away = collections.Counter((r["type"], r["core"]) for r in rows)
fig, axs = plt.subplots(2, 2, figsize=(22, 16))
def draw(ax, tn, zoom=None):
    t = G[tn]; w, hh = t["outline_um"]
    ax.add_patch(Rectangle((0, 0), w, hh, fill=False, lw=1.5))
    bh = {h["inst"]: h for h in B[tn]["hard_cores"]}
    for h in t["hard_cores"]:
        x, y = h["origin_um"]; cw, ch = h["outline_um"]
        if zoom and not (x < zoom[2] and x + cw > zoom[0] and y < zoom[3] and y + ch > zoom[1]): continue
        reo = bh[h["inst"]].get("orient", "R0") != h.get("orient", "R0")
        ax.add_patch(Rectangle((x, y), cw, ch, fc="orange" if reo else "0.92", ec="red" if away[(tn, h["inst"])] else "0.5",
                               lw=2 if away[(tn, h["inst"])] else 0.5, alpha=0.6))
        if zoom or reo or away[(tn, h["inst"])]:
            lab = h["inst"].replace("u_", "") + (f"\n{bh[h['inst']].get('orient','R0')}->{h.get('orient','R0')}" if reo else "") + (f"\naway {away[(tn, h['inst'])]}" if away[(tn, h['inst'])] else "")
            ax.text(x + cw / 2, y + ch / 2, lab, fontsize=6 if not zoom else 9, ha="center", va="center")
        f = h.get("pins_file")
        if not f: continue
        pb = {pname(p): (p["x"], p["y"]) for p in pins(b, f)}; pg = pins(g, f)
        mv = [p for p in pg if pb.get(pname(p)) != (p["x"], p["y"])]
        st = pg[:: max(1, len(pg) // 400)]
        if zoom or reo or mv:
            xs, ys = zip(*[tf(h, p["x"], p["y"]) for p in st]); ax.scatter(xs, ys, s=1, c="0.4")
        if mv:
            xs, ys = zip(*[tf(h, p["x"], p["y"]) for p in mv]); ax.scatter(xs, ys, s=3 if not zoom else 8, c="tab:blue")
    if zoom: ax.set_xlim(zoom[0], zoom[2]); ax.set_ylim(zoom[1], zoom[3])
    else: ax.set_xlim(-50, w + 50); ax.set_ylim(-50, hh + 50)
    ax.set_aspect("equal"); ax.set_title(f"{tn} C17g {'zoom ' + str(zoom) if zoom else ''}: orange = re-oriented, red edge = G0C away ports left, blue = moved pins")
draw(axs[0][0], "q_hub_nw"); draw(axs[0][1], "q_hub_ne")
draw(axs[1][0], "q_hub_nw", (1100, 2350, 1750, 3100)); draw(axs[1][1], "q_hub_nw", (1950, 750, 2450, 1300))
plt.tight_layout(); plt.savefig(outp, dpi=80)
