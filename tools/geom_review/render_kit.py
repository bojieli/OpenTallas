#!/usr/bin/env python3
"""Render a die-plan G3 kit (pre-place review): outline, plan pins by bus, clock tap grid (+ nearest-tap Voronoi),
reset entry + relay tree (from reset_tree.tcl + kit RTL), face-flop bands, PG straps if pdn.tcl lists them.
usage: render_kit.py KITDIR OUT.png"""
import json, re, sys
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
K = Path(sys.argv[1]); out = sys.argv[2]
b = json.load(open(K / "budget.json")); W, H = b["outline_um"]
pins = json.load(open(K / "pins.json"))
fig, ax = plt.subplots(1, 2, figsize=(16, 13), gridspec_kw=dict(width_ratios=[3, 1.2]))
a = ax[0]
a.add_patch(Rectangle((0, 0), W, H, fill=False, lw=2))
buses = sorted({p["bus"] for p in pins})
cm = plt.get_cmap("tab10")
col = {bn: cm(i % 10) for i, bn in enumerate(buses)}
from collections import defaultdict
stat = defaultdict(lambda: dict(n=0, faces=set(), layers=set(), lo=1e9, hi=-1e9))
for p in pins:
    s = stat[p["bus"]]; s["n"] += 1; s["faces"].add(p["face"]); s["layers"].add(p["layer"])
    c = p["x"] if p["face"] in "NS" else p["y"]; s["lo"] = min(s["lo"], c); s["hi"] = max(s["hi"], c)
    d = 12
    x, y = p["x"], p["y"]
    dx, dy = {"N": (0, -d), "S": (0, d), "E": (-d, 0), "W": (d, 0)}[p["face"]]
    a.plot([x, x + dx], [y, y + dy], color=col[p["bus"]], lw=0.4)
# taps
taps = b["clock"].get("taps_snapped") or b["clock"]["taps"]
for t in taps:
    a.plot(*t["xy"], marker="*", ms=18, color="gold", mec="k")
    a.annotate(t["name"], t["xy"], xytext=(6, 6), textcoords="offset points", fontsize=8)
# nearest-tap regions (grid lines between taps)
xs = sorted({round(t["xy"][0], 1) for t in taps}); ys = sorted({round(t["xy"][1], 1) for t in taps})
for i in range(len(xs) - 1): a.axvline((xs[i] + xs[i + 1]) / 2, color="gold", ls=":", lw=1)
for i in range(len(ys) - 1): a.axhline((ys[i] + ys[i + 1]) / 2, color="gold", ls=":", lw=1)
# reset tree
sites = {}
for ln in (K / "reset_tree.tcl").read_text().splitlines():
    m = re.match(r"rtr_place (\S+) \{\*(u_\w+)\[\./\]\*\} ([\d.]+) ([\d.]+) (\S+)", ln)
    if m: sites[m.group(2)] = (m.group(1), float(m.group(3)), float(m.group(4)), m.group(5))
net_at = {v[0]: (v[1], v[2]) for v in sites.values()}
rtl = "".join(p.read_text() for p in (K / "rtl").glob("*_bound.sv"))
edges = re.findall(r"ot_dp_rrelay (u_\w+) \(\.clk\(clk\), \.d\((\w+)\), \.q\((\w+)\)\)", rtl)
ap = None
for ln in (K / "io.tcl").read_text().splitlines():
    m = re.match(r"place_pin -pin_name arst_n -layer \S+ -location \{([\d.]+) ([\d.]+)\}", ln)
    if m: ap = (float(m.group(1)), float(m.group(2)))
if ap: net_at["arst_n"] = ap; a.plot(*ap, "s", ms=10, color="red", mec="k"); a.annotate("arst_n pin", ap, xytext=(6, -12), textcoords="offset points", fontsize=8, color="red")
nrel = 0
for inst, d, q in edges:
    if d in net_at and q in net_at:
        (x0, y0), (x1, y1) = net_at[d], net_at[q]
        a.annotate("", (x1, y1), (x0, y0), arrowprops=dict(arrowstyle="->", color="red", lw=1.2))
    if q in net_at: a.plot(*net_at[q], "o", ms=6, color="red"); nrel += 1
# face-flop bands (pin regs at their pins, p90 budget 30 um)
for f in "NSEW":
    fp = [p for p in pins if p["face"] == f]
    if not fp: continue
    if f in "NS":
        y = H - 30 if f == "N" else 0
        a.add_patch(Rectangle((min(p["x"] for p in fp), y), max(p["x"] for p in fp) - min(p["x"] for p in fp), 30, alpha=0.12, color="blue"))
    else:
        x = W - 30 if f == "E" else 0
        a.add_patch(Rectangle((x, min(p["y"] for p in fp)), 30, max(p["y"] for p in fp) - min(p["y"] for p in fp), alpha=0.12, color="blue"))
a.set_xlim(-40, W + 40); a.set_ylim(-40, H + 40); a.set_aspect("equal")
a.set_title(f"{b['type']} G3 kit {W}x{H} um: pins by bus, clock taps (*), reset entry+relays (red), face-flop bands (blue, 30 um)", fontsize=10)
for bn in buses: a.plot([], [], color=col[bn], lw=3, label=bn)
a.legend(loc="upper right", fontsize=8)
t = ax[1]; t.axis("off")
lines = [f"pins {len(pins)}  taps {len(taps)}  reset relays {nrel} (+entry)"]
for bn in buses:
    s = stat[bn]; span = s["hi"] - s["lo"]
    lines.append(f"{bn}: {s['n']} pins face {''.join(sorted(s['faces']))} {','.join(sorted(s['layers']))} span {s['lo']:.1f}-{s['hi']:.1f} ({s['n']/max(span,1):.2f}/um)")
extra = Path(K / "review_extra.txt")
if extra.exists(): lines += [""] + extra.read_text().splitlines()
t.text(0, 1, "\n".join(lines), va="top", family="monospace", fontsize=8, wrap=True)
fig.tight_layout(); fig.savefig(out, dpi=110)
print("wrote", out)
