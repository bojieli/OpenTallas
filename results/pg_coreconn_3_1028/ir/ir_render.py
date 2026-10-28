#!/usr/bin/env python3
"""PG-CORECONN-3: render a tile's co-located drop map: std-cell VDD drop + VSS bounce (max per 4.32-um bin), macro outlines
from the kit macro_place.tcl + LEF sizes (orientation swaps none for R0/MX/MY/R180).  ir_render.py DIR TAG KIT OUT.png [zoom x0 y0 x1 y1]"""
import csv, glob, re, sys
from collections import defaultdict
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
d, tag, kit, out = sys.argv[1:5]; zoom = list(map(float, sys.argv[5:9])) if len(sys.argv) > 8 else None
B = 4.32; g = defaultdict(float)
for net in ("VDD", "VSS"):
    m = defaultdict(float)
    for r in csv.DictReader(open(f"{d}/volt_{tag}_{net}.rpt")):
        if r["Instance"].startswith("pgl_"): continue
        v = float(r["Voltage"]); dv = 0.7 - v if net == "VDD" else v
        k = (int(float(r["X location"]) // B), int(float(r["Y location"]) // B)); m[k] = max(m[k], dv)
    for k, v in m.items(): g[k] += v
sz = {}
for f in glob.glob(f"{kit}/macros/*.lef"):
    t = open(f).read()
    for mm in re.finditer(r"MACRO (\S+)(.*?)END \1", t, re.S):
        s = re.search(r"SIZE ([\d.]+) BY ([\d.]+)", mm.group(2))
        if s: sz[mm.group(1)] = (float(s.group(1)), float(s.group(2)))
mac = []
for ln in open(f"{kit}/macro_place.tcl"):
    p = re.search(r"-macro_name \{(\S+)\} -location \{([\d.]+) ([\d.]+)\}", ln)
    if p: mac.append((p.group(1), float(p.group(2)), float(p.group(3))))
fig, ax = plt.subplots(figsize=(11, 9.5))
xs = [k[0] * B for k in g]; ys = [k[1] * B for k in g]; cs = [1e3 * v for v in g.values()]
sc = ax.scatter(xs, ys, c=cs, s=2 if not zoom else 12, marker="s", cmap="inferno", vmin=0, vmax=max(cs))
plt.colorbar(sc, label="std-cell VDD drop + VSS bounce, mV (max per 4.32 um bin)")
mast = {}
import subprocess
for ln in open(f"{kit}/macro_place.tcl"): pass
# master per instance from the synth netlist is not needed: draw every placed macro with the largest LEF matching by name order
for name, x, y in mac:
    # kit 1_synth_odb.v holds "<master> <inst>" pairs; fall back to an unlabeled 10x10 box
    mast.setdefault(name, None)
v = open(f"{kit}/1_synth_odb.v").read() if glob.glob(f"{kit}/1_synth_odb.v") else ""
for name, x, y in mac:
    esc = re.escape(name.replace(".", "\\.") if False else name)
    m = re.search(r"\n\s*(\w+)\s+\\?" + re.escape(name) + r"\s*\(", v) or re.search(r"\n\s*(\w+)\s+" + re.escape(name.split(".")[-1]) + r"\s*\(", v)
    w, h = sz.get(m.group(1), (10, 10)) if m else (10, 10)
    ax.add_patch(Rectangle((x, y), w, h, fill=False, ec="cyan", lw=0.6))
if zoom: ax.set_xlim(zoom[0], zoom[2]); ax.set_ylim(zoom[1], zoom[3])
ax.set_aspect("equal"); ax.set_title(f"{tag}: worst {max(cs):.2f} mV; cyan = placed macros (distributed core loads)")
plt.savefig(out, dpi=110, bbox_inches="tight"); print(out, max(cs))
