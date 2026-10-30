import sys, json, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
a, b, png, js = sys.argv[1:5]
def rd(p):
    d = {}; die = None
    for l in open(p):
        t = l.split()
        if t[0] == "DIE": die = (float(t[1]), float(t[2])); continue
        d[t[0]] = (t[1], *map(float, t[2:6]), t[6])
    return die, d
die, A = rd(a); _, B = rd(b)
new = {k: v for k, v in B.items() if k not in A}
gone = [k for k in A if k not in B]
moved = {k: max(abs(B[k][1]-A[k][1]), abs(B[k][2]-A[k][2])) for k in A if k in B and (B[k][1], B[k][2]) != (A[k][1], A[k][2])}
mast = {k: (A[k][0], B[k][0]) for k in A if k in B and A[k][0] != B[k][0]}
macros = [v for v in B.values() if v[0].startswith("ot_sram")]
inmac = [k for k, v in new.items() if any(m[1] < (v[1]+v[3])/2 < m[3] and m[2] < (v[2]+v[4])/2 < m[4] for m in macros)]
ffmast = [k for k, (x, y) in mast.items() if x.startswith("DFF") or y.startswith("DFF")]
ffmoved = [k for k in moved if A[k][0].startswith("DFF")]
from collections import Counter
r = dict(new=len(new), new_masters=Counter(v[0] for v in new.values()).most_common(8), gone=len(gone), moved=len(moved),
         moved_max_um=round(max(moved.values()), 3) if moved else 0, master_changes=len(mast), ff_master_changes=len(ffmast),
         ff_moved=len(ffmoved), new_inside_macro=len(inmac))
json.dump(r, open(js, "w"), indent=1); print(r)
fig, ax = plt.subplots(figsize=(14, 8))
ax.add_patch(Rectangle((0, 0), *die, fill=False, lw=1))
for m in macros: ax.add_patch(Rectangle((m[1], m[2]), m[3]-m[1], m[4]-m[2], color="#bbbbbb"))
xs = [(v[1]+v[3])/2 for v in A.values() if not v[0].startswith("ot_sram")]; ys = [(v[2]+v[4])/2 for v in A.values() if not v[0].startswith("ot_sram")]
ax.scatter(xs, ys, s=0.2, c="#9ab")
for k, v in new.items():
    c = "orange" if k.startswith("hold") else "red"
    ax.scatter([(v[1]+v[3])/2], [(v[2]+v[4])/2], s=10, c=c, marker="s")
for k in moved: v = B[k]; ax.scatter([(v[1]+v[3])/2], [(v[2]+v[4])/2], s=3, c="blue")
for x, y in [(20.574, 8.505), (18.36, 7.965), (13.176, 9.585)]: ax.scatter([x], [y], s=80, facecolors="none", edgecolors="green", lw=2)
ax.add_patch(Rectangle((159.9, 98.0), 1.2, 1.3, fill=False, ec="magenta", lw=2))
ax.set_xlim(0, die[0]); ax.set_ylim(0, die[1]); ax.set_aspect("equal")
ax.set_title(f"BTAB PRD ECO {png}: new {len(new)} (red repair, orange hold), moved {len(moved)} blue, green=3 hold EP sinks, magenta=DRC3 window")
plt.savefig(png, dpi=110, bbox_inches="tight")
