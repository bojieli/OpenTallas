"""QC-SU-PROG-L1: render an ht_l1 spec (tree nodes + parent legs as L paths, islands, SRAMs, E pin columns, x=283 line)."""
import json, sys, re
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
r = json.load(open(sys.argv[1])); g = json.load(open(r["gate_json"])); geo = g["geo"]
fig, ax = plt.subplots(figsize=(13, 9.5))
for line in open(geo):
    f = line.split()
    if f and f[0] == "CORE": c = list(map(float, f[1:5])); ax.add_patch(Rectangle((c[0], c[1]), c[2]-c[0], c[3]-c[1], fill=False))
    if f and f[0] == "MACRO":
        x0, y0, x1, y1 = map(float, f[3:7]); ax.add_patch(Rectangle((x0, y0), x1-x0, y1-y0, fc="#bbb", ec="k"))
    if f and f[0] == "PIN": ax.plot(float(f[2]), float(f[3]), "k*", ms=12)
for q in g["gates"]["G5_sram_structure"]["pin_columns_um"]:
    ax.add_patch(Rectangle((q[0], q[1]), q[2]-q[0], q[3]-q[1], fc="orange", alpha=0.3, ec="none"))
ax.axvline(r["xcol_E"] + 4.32, color="orange", ls="--", lw=0.8)
t = open(r["spec"]).read().split("set ot_ms_tree {")[1].split("\n}")[0]
pos = {"root": tuple(map(float, re.search(r"set ot_ms_root \{([\d.]+) ([\d.]+)\}", open(r["spec"]).read()).groups()))}
nd = {}
for ln in t.strip().splitlines():
    f = ln.strip().strip("{}").split(); nd[f[0]] = f[1]; pos[f[0]] = (float(f[2]), float(f[3]))
for n, p in nd.items():
    a, b = pos[p], pos[n]
    l1 = re.fullmatch(r"(T[EW](_r\d+)?|Q\d+(_h\d+)?)", n) is not None
    ax.plot([a[0], a[0], b[0]], [a[1], b[1], b[1]], "-", color="red" if l1 else "blue", lw=1.8 if l1 else 0.7)
    ax.plot(*b, "s", color="purple", ms=3.5 if not re.fullmatch(r"Q\d+|T[EW]", n) else 6)
for i in g["gates"]["G2_island_rows"]["islands"]:
    R = i["rect_um"]; ax.add_patch(Rectangle((R[0], R[1]), R[2]-R[0], R[3]-R[1], fc="magenta", ec="k"))
p = r["phys"]
ax.set_aspect("equal"); ax.set_title(f"{sys.argv[1].split('/')[-1]} struct {r['structure_verdict']} gate {r['verdict']}  uf_phys TT rise {p['TT_rise']['mean']} w{p['TT_rise']['window']}  FF early {p['FF_early']['mean']} w{p['FF_early']['window']}\n"
             f"H-tree L1 red (trunks {r['trunk_len_um']}, legs {r['leg_len_um']}), L2/L3 blue (drawn as L paths), islands magenta, E pin columns orange, dashed = column + 4.32", fontsize=8)
plt.savefig(sys.argv[2], dpi=110, bbox_inches="tight")
