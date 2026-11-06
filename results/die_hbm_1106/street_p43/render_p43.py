#!/usr/bin/env python3
"""render_p43.py BASE_GZ NEW_GZ LEDGER OUT.png: part 43 touched types (cores grey, clock keep-outs pink, old station
points red x, new points green o, arrows old->new, bit sites of the touched stage small blue)."""
import gzip, json, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
A = json.loads(gzip.open(sys.argv[1]).read()); B = json.loads(gzip.open(sys.argv[2]).read())
L = json.load(open(sys.argv[3])); out = sys.argv[4]
types = ["q_b000", "q_b001", "q_b010", "q_b011", "q_b102"]
fig, axs = plt.subplots(1, 5, figsize=(30, 12))
for ax, tn in zip(axs, types):
    T = B["partition_types"][tn]; w, h = T["outline_um"]
    ax.add_patch(Rectangle((0, 0), w, h, fill=False, ec="k", lw=1))
    for hc in T.get("hard_cores") or []:
        x, y = hc["origin_um"]; cw, ch = hc["outline_um"]
        ax.add_patch(Rectangle((x, y), cw, ch, fc="0.85", ec="0.4", lw=0.5))
    for k in (T.get("clock") or {}).get("keepouts_um") or []:
        ax.add_patch(Rectangle((k[0], k[1]), k[2] - k[0], k[3] - k[1], fc="pink", ec="r", lw=0.5, alpha=0.6))
    so = {s["name"]: s for s in A["partition_types"][tn]["ft_slots"]}
    for s in T["ft_slots"]:
        r0 = so[s["name"]].get("regs_um"); r1 = s.get("regs_um")
        if r0 == r1:
            continue
        for j, (p, q) in enumerate(zip(r0, r1)):
            if p == q:
                continue
            if s.get("bit_sites_um"):
                st = s["bit_sites_um"][j - 1]
                ax.scatter([a[0] for a in st[::7]], [a[1] for a in st[::7]], s=0.2, c="tab:blue")
            ax.plot(*p, "rx", ms=8); ax.plot(*q, "go", ms=6, mfc="none")
            ax.annotate("", q, p, arrowprops=dict(arrowstyle="->", color="g", lw=0.8))
            ax.text(q[0] + 4, q[1] + 4, f"{s['name']}#{j}", fontsize=6, color="g")
    ax.set_xlim(-10, w + 10); ax.set_ylim(-10, h + 10); ax.set_aspect("equal")
    ax.set_title(f"{tn}: part 43 (x old, o new)")
fig.tight_layout(); fig.savefig(out, dpi=80)
print("wrote", out)
