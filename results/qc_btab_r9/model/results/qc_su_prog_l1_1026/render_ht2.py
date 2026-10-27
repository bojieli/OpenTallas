"""QC-SU-PROG-L2: render an ht_l2 result: SRAMs, pin columns + clearance band, L1 L-paths (red), L2 island->sub-island maze legs
(green), L3/L4 maze legs (blue), islands (magenta), sub-islands (green squares).  usage: render_ht2.py X.ht2.json OUT.png"""
import json, sys, re
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
r = json.load(open(sys.argv[1])); geo = r["inputs"]["geo"]; g = json.load(open(r["inputs"]["gate_json"]))
fig, ax = plt.subplots(figsize=(13, 9.5))
for line in open(geo):
    f = line.split()
    if f and f[0] == "CORE": c = list(map(float, f[1:5])); ax.add_patch(Rectangle((c[0], c[1]), c[2]-c[0], c[3]-c[1], fill=False))
    if f and f[0] == "MACRO":
        x0, y0, x1, y1 = map(float, f[3:7]); ax.add_patch(Rectangle((x0, y0), x1-x0, y1-y0, fc="#bbb", ec="k"))
    if f and f[0] == "PIN": ax.plot(float(f[2]), float(f[3]), "k*", ms=12)
    if f and f[0] == "SINK": ax.plot(float(f[1]), float(f[2]), ",", color="#777")
C = r["clearance_um"]
for q in g["gates"]["G5_sram_structure"]["pin_columns_um"]:
    ax.add_patch(Rectangle((q[0], q[1]), q[2]-q[0], q[3]-q[1], fc="orange", alpha=0.35, ec="none"))
    ax.add_patch(Rectangle((q[0]-C, q[1]), q[2]-q[0]+2*C, q[3]-q[1], fill=False, ec="orange", ls="--", lw=0.6))
for n, p in r["l1_legs"].items():
    ax.plot([x for x, _ in p], [y for _, y in p], "-", color="red", lw=1.8)
for n, p in r["legs"].items():
    lev2 = re.fullmatch(r"Q\d+S\d+", n) is not None
    ax.plot([x for x, _ in p], [y for _, y in p], "-", color="green" if lev2 else "blue", lw=1.6 if lev2 else 0.7)
for i in g["gates"]["G2_island_rows"]["islands"]:
    R = i["rect_um"]; ax.add_patch(Rectangle((R[0], R[1]), R[2]-R[0], R[3]-R[1], fc="magenta", ec="k"))
for s, v in r["sub_islands"].items():
    R = v["rect"]; ax.add_patch(Rectangle((R[0], R[1]), R[2]-R[0], R[3]-R[1], fc="lime", ec="k")); ax.text(R[2], R[3], s, fontsize=6)
t = open(r["spec"]).read().split("set ot_ms_tree {")[1].split("\n}")[0]
for ln in t.strip().splitlines():
    f = ln.strip().strip("{}").split(); ax.plot(float(f[2]), float(f[3]), "s", color="purple", ms=2.5)
p = r["phys"]
ax.set_aspect("equal")
ax.set_title(f"{sys.argv[1].split('/')[-1]}  struct {r['structure_verdict']}  gate {r['verdict']}  D2 {r['D2_um']} seg {r['seg_um']}  uf_phys(refit4) TT rise {p['TT_rise']['mean']} w{p['TT_rise']['window']}  FF early {p['FF_early']['mean']} w{p['FF_early']['window']}\n"
             "L1 red, L2 island->sub-island green (maze), L3/L4 blue (maze), islands magenta, sub-islands lime, pin columns orange, dashed = clearance band", fontsize=8)
plt.savefig(sys.argv[2], dpi=110, bbox_inches="tight")
