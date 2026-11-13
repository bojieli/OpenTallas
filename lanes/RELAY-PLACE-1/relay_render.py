"""relay_render.py GEOM_RULES_DIR geom.tsv out.png title : relay/station flops of a placed kit; chain hops > 405 um red."""
import sys, re
sys.path.insert(0, sys.argv[1])
import site; site.addsitedir("/home/ubuntu/.local/lib/python3.14/site-packages")
import geom_rules as G
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

D = G.Design(sys.argv[2])
src = {}
for cid, c in D.cells.items():
    if c[0] != "S":
        continue
    ins = [n for n, isc in D.cell_in.get(cid, []) if not isc]
    if len(ins) != 1:
        continue
    cur, depth, prev = ins[0], 0, None
    while depth <= G.PINREG_DEPTH:
        dr = D.nets[cur][1]
        if not dr or dr[0] != "i":
            break
        k = D.kind(dr[1])
        if k == "S":
            prev = dr[1]; break
        if k != "B" or not D.cell_in.get(dr[1]):
            break
        cur = D.cell_in[dr[1]][0][0]; depth += 1
    if prev is not None and prev != cid:
        src[cid] = prev
REL = re.compile(r"u_ft_|u_fx|u_srl|u_rrl|u_y_|u_cland")
fig, ax = plt.subplots(figsize=(11, 9.5), dpi=110)
X0, Y0, X1, Y1 = D.die
ax.add_patch(plt.Rectangle((X0, Y0), X1 - X0, Y1 - Y0, fill=False, lw=1, ec="k"))
other = [G.ctr(c) for c in D.cells.values() if c[0] in "SB" and not REL.search(c[6])]
if other:
    ax.scatter(*zip(*other), s=0.05, c="#c8c8c8", lw=0, rasterized=True)
slots = {}
for cid, c in D.cells.items():
    if c[0] == "S" and REL.search(c[6]):
        m = re.search(r"u_(ft|fx)_?([A-Za-z0-9]+?)_[io]_?(\d+)", c[6])
        key = m.group(2) if m else ("ring" if "u_cland" in c[6] else "reset" if re.search("u_srl|u_rrl", c[6]) else "relay")
        slots.setdefault(key, []).append(G.ctr(c))
cmap = plt.get_cmap("tab20")
for i, (k, pts) in enumerate(sorted(slots.items())):
    ax.scatter(*zip(*pts), s=0.6, color=cmap(i % 20), lw=0, rasterized=True)
good, bad, mh = [], [], 0.0
for s, p in src.items():
    a, b = D.cells[s], D.cells[p]
    if not (REL.search(a[6]) and REL.search(b[6])):
        continue
    pa, pb = G.ctr(a), G.ctr(b)
    h = abs(pa[0] - pb[0]) + abs(pa[1] - pb[1])
    if "u_cland" in a[6] and "u_cland" in b[6]:
        continue
    mh = max(mh, h)
    (bad if h > 405.0 else good).append([pb, pa])
ax.add_collection(LineCollection(good, colors="#2a7ab8", linewidths=0.08, alpha=0.25))
ax.add_collection(LineCollection(bad, colors="#d62728", linewidths=0.6))
ax.set_aspect("equal"); ax.set_xlim(X0 - 10, X1 + 10); ax.set_ylim(Y0 - 10, Y1 + 10)
ax.set_title(f"{sys.argv[4]}\nrelay/station hops: {len(good) + len(bad)}, > 405 um: {len(bad)} (red), max {mh:.0f} um", fontsize=10)
ax.set_xlabel("um"); fig.tight_layout(); fig.savefig(sys.argv[3])
print("RENDER", sys.argv[3], "hops", len(good) + len(bad), "over405", len(bad), "max", round(mh, 1))
