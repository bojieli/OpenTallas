#!/usr/bin/env python3
"""PATH-QC-NK render: NK 4_cts sinks coloured by FF clock arrival, hard children boxed with tap + effective arrival,
tap ports, worst FF hold paths by class.  render.py PREFIX OUT.png [title]"""
import csv, sys, collections
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P, OUT = sys.argv[1], sys.argv[2]; title = sys.argv[3] if len(sys.argv) > 3 else P
LAT_FF = {"ot_qwen_tile_romleaf": 173.9, "ot_qwen_tile_lsl_fp1": 133.9, "ot_qwen_tile_node": 199.6}
SIZE = {"ot_qwen_tile_romleaf": (77.0, 123.0), "ot_qwen_tile_lsl_fp1": (90.0, 150.0), "ot_qwen_tile_node": (75.0, 160.0)}
TAPS = {}
import re
for l in open(sys.argv[4] if len(sys.argv) > 4 else "/srv/opentallas-scratch2/claude/path-qc-nk/r5d/src/tools/qwen_romleaf/a0core/qfd_tile_nk_a0c8_pins.tcl"):
    m = re.search(r"-pin_name \{(ck(?:_t\d+)?)\} -layer M7 -location \{([\d.]+) ([\d.]+)\}", l)
    if m: TAPS[m.group(1)] = (float(m.group(2)), float(m.group(3)))
sinks = [r[:3] + r[3].split() for r in csv.reader(open(P + ".sinks.tsv"), delimiter="\t") if len(r) >= 4 and r[0] != "inst" and r[2] not in ("-", "")]
cores = list(csv.DictReader(open(P + ".cores.tsv"), delimiter="\t"))
paths = list(csv.DictReader(open(P + ".tsv"), delimiter="\t"))
fig, ax = plt.subplots(1, 2, figsize=(22, 26), gridspec_kw={"width_ratios": [1, 1]})
for k, a in enumerate(ax):
    a.add_patch(Rectangle((0, 0), 457.92, 1157.76, fill=False, lw=1.5))
    for c in cores:
        if c["x"] == "-": continue
        w, h = float(c["w"]), float(c["h"])
        x, y = float(c["x"]), float(c["y"])
        try: eff = float(c["clk_ff_max"]) + LAT_FF[c["master"]]
        except ValueError: eff = float("nan")
        a.add_patch(Rectangle((x - w / 2, y - h / 2), w, h, fill=True, alpha=0.15, color="gray"))
        a.text(x, y, f"{c['master'].split('_')[-1]}\n{c['tap']}\npin {float(c['clk_ff_max']):.0f}\neff {eff:.0f}", ha="center", va="center", fontsize=7)
    for t, (x, y) in TAPS.items():
        a.plot(x, y, marker="^", color="k", ms=6); a.text(x + 2, y + 2, t, fontsize=6)
    a.set_xlim(-5, 463); a.set_ylim(-5, 1163); a.set_aspect("equal")
xs = [float(r[3]) for r in sinks]; ys = [float(r[4]) for r in sinks]; cs = [float(r[2]) for r in sinks]
sc = ax[0].scatter(xs, ys, c=cs, s=1, cmap="turbo", vmin=100, vmax=360)
fig.colorbar(sc, ax=ax[0], fraction=0.03, label="FF clock arrival at sink CLK (ps)")
ax[0].set_title(f"{title}\nsinks by FF clock arrival (triangles = tap ports; boxes = hard children, eff = pin + FF mean internal)")
cols = {}
palette = ["red", "blue", "green", "magenta", "orange", "cyan", "brown", "olive", "purple", "black"]
cnt = collections.Counter(p["class"] for p in paths)
for i, (k, n) in enumerate(cnt.most_common()):
    cols[k] = palette[i % len(palette)]
drawn = collections.Counter()
for p in sorted(paths, key=lambda p: float(p["slack"])):
    if drawn[p["class"]] >= 60: continue
    try: sx, sy, ex, ey = float(p["sx"]), float(p["sy"]), float(p["ex"]), float(p["ey"])
    except ValueError:
        if p["ex"] not in ("-", ""): ax[1].plot(float(p["ex"]), float(p["ey"]), "x", color=cols[p["class"]], ms=4)
        continue
    drawn[p["class"]] += 1
    ax[1].plot([sx, ex], [sy, ey], "-", color=cols[p["class"]], lw=0.7)
    ax[1].plot(sx, sy, "s", color=cols[p["class"]], ms=2); ax[1].plot(ex, ey, "x", color=cols[p["class"]], ms=4)
for k, n in cnt.most_common():
    v = [float(p["slack"]) for p in paths if p["class"] == k]
    ax[1].plot([], [], color=cols[k], label=f"{k}: n={n} wns={min(v):.1f}")
ax[1].legend(loc="upper right", fontsize=8)
ax[1].set_title(f"FF hold violators by class ({len(paths)} endpoints; worst 60/class drawn, square=start x=end; IN ports: end only)")
fig.tight_layout(); fig.savefig(OUT, dpi=80)
print("wrote", OUT)
