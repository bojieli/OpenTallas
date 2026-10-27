#!/usr/bin/env python3
"""HEAD-CORE-LAT-R5: render a head core geo (dump_geo_head.tcl format): sinks, macros, entry, quadrant sink counts.
usage: head_geo_render.py GEO OUT.png TITLE [--entry X,Y]"""
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

geo, out, title = sys.argv[1:4]
entry = None
if "--entry" in sys.argv:
    entry = tuple(map(float, sys.argv[sys.argv.index("--entry") + 1].split(",")))
S, M, die, ports = [], [], None, {}
for ln in open(geo):
    f = ln.split()
    if not f:
        continue
    if f[0] == "SINK":
        S.append((float(f[1]), float(f[2])))
    elif f[0] == "MACRO":
        M.append((f[1], tuple(map(float, f[3:7])), (float(f[8]), float(f[9]))))
    elif f[0] == "DIE":
        die = tuple(map(float, f[1:5]))
    elif f[0] == "PORT":
        ports[f[1]] = (float(f[2]), float(f[3]))
cx, cy = entry or ((die[0] + die[2]) / 2, (die[1] + die[3]) / 2)
q = {k: 0 for k in ("WS", "WN", "ES", "EN")}
for x, y in S:
    q[("W" if x < cx else "E") + ("S" if y < cy else "N")] += 1
far = max(abs(x - cx) + abs(y - cy) for x, y in S)
fig, ax = plt.subplots(figsize=(9, 9))
ax.add_patch(Rectangle((die[0], die[1]), die[2] - die[0], die[3] - die[1], fill=False, lw=1.5))
ax.scatter([s[0] for s in S], [s[1] for s in S], s=0.4, c="0.45", lw=0)
for nm, r, p in M:
    ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc="0.85", ec="k"))
    ax.text(r[0] + 2, r[3] - 6, nm, fontsize=8)
    ax.plot(*p, "ks", ms=4)
ax.plot(cx, cy, "r*", ms=16, label="clock entry (centre island)")
for nm, p in ports.items():
    ax.plot(*p, "b^", ms=5)
ax.axvline(cx, color="r", lw=0.4, ls="--"); ax.axhline(cy, color="r", lw=0.4, ls="--")
ax.set_xlim(die[0] - 5, die[2] + 5); ax.set_ylim(die[1] - 5, die[3] + 5); ax.set_aspect("equal")
ax.set_title("%s\n%d sinks, quadrants WS/WN/ES/EN %d/%d/%d/%d, max entry->sink Manhattan %.1f um"
             % (title, len(S), q["WS"], q["WN"], q["ES"], q["EN"], far), fontsize=9)
ax.legend(loc="upper right", fontsize=8)
fig.savefig(out, dpi=110, bbox_inches="tight")
print("RENDER", out, len(S), q, round(far, 1))
