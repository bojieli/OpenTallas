"""HBM-EP-ROUTE-1 routed render: routed clock wires (colour = layer) + clock buffers + SRAM macros.
python3 render_routed.py routed_clk.txt out.png title"""
import sys, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
col = {"M2": "#1f77b4", "M3": "#2ca02c", "M4": "#ff7f0e", "M5": "#d62728", "M1": "#7f7f7f"}
fig, ax = plt.subplots(figsize=(9, 12)); ax.add_patch(plt.Rectangle((0, 0), 250.56, 375.84, fill=False, lw=1.5))
seen = set()
for l in open(sys.argv[1]):
    f = l.split()
    if f[0] == "M":
        x0, y0, x1, y1 = map(float, f[2:6]); ax.add_patch(plt.Rectangle((x0, y0), x1-x0, y1-y0, fc="#dddddd", ec="gray"))
for l in open(sys.argv[1]):
    f = l.split()
    if f[0] == "W":
        x0, y0, x1, y1 = map(float, f[2:6]); lab = f[1] if f[1] not in seen else None; seen.add(f[1])
        trunk = any(k in f[6] for k in ("T00_br_n", "T10_br_n", "T01_br_n", "T11_br_n"))
        ax.plot([x0, x1], [y0, y1], "-", color=col.get(f[1], "k"), lw=1.6 if trunk else 0.35, label=lab)
    elif f[0] == "B":
        x, y = float(f[3]), float(f[4]); e = "entry" in f[1]
        ax.plot(x, y, "*" if e else "o", mfc="none" if not e else "b", mec="b" if e else "k", ms=7 if e else 2.5)
ax.plot(125.28, 187.92, "b*", ms=14)
ax.legend(loc="upper right", fontsize=8); ax.set_aspect("equal"); ax.set_xlim(-5, 256); ax.set_ylim(-5, 381)
ax.set_title(sys.argv[3], fontsize=9); fig.tight_layout(); fig.savefig(sys.argv[2], dpi=120)
