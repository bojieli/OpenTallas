# render: routed clock wires (M4 blue / M5 orange / M2-M3 black), vias of clock nets (dots), PG straps faint, macros grey,
# clock cells, register clock pins coloured by RCX TT arrival (meas_ck tsv; placement from FF positions not in tsv -> use
# leaf tap cells coloured by their leaf mean RCX-GRT delta).  usage: ck_render.py OUT.png TITLE wires.txt grt_TT.tsv rcx_TT.tsv
import sys, re, statistics as st, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
out, title, wf, gf, rf = sys.argv[1:6]
def leaf(fn):
    d = {}
    for l in open(fn):
        if l.startswith("#"): continue
        f = l.split("\t"); m = re.fullmatch(r"ot_ms_(Q\w+?)_clk", f[1])
        if m: d.setdefault(m.group(1), []).append(float(f[2]))
    return {k: st.mean(v) for k, v in d.items()}
g, r = leaf(gf), leaf(rf)
segs = {"M4": [], "M5": [], "lo": []}; vias = []; mac = []; ck = []; pg = []
for l in open(wf):
    f = l.split()
    if f[0] == "W":
        x0, y0, x1, y1 = map(float, f[3:7]); L = f[2] if f[2] in ("M4", "M5") else "lo"
        segs[L].append([((x0 + x1) / 2, y0), ((x0 + x1) / 2, y1)] if (y1 - y0) > (x1 - x0) else [(x0, (y0 + y1) / 2), (x1, (y0 + y1) / 2)])
    elif f[0] == "VIA": vias.append((float(f[2]), float(f[3])))
    elif f[0] == "MACRO": mac.append(tuple(map(float, f[2:6])))
    elif f[0] == "CK": ck.append((f[1], f[2], float(f[3]), float(f[4])))
    elif f[0] == "PG": pg.append((f[1], *map(float, f[2:6])))
fig, ax = plt.subplots(figsize=(13, 11.5))
for m in mac: ax.add_patch(plt.Rectangle((m[0], m[1]), m[2] - m[0], m[3] - m[1], color="0.85", zorder=0))
for p in pg:
    ax.add_patch(plt.Rectangle((p[1], p[2]), max(p[3] - p[1], 0.3), max(p[4] - p[2], 0.3), color=("#c9a0dc" if p[0] == "M5" else "#a0c4dc"), alpha=.35, lw=0, zorder=1))
ax.add_collection(LineCollection(segs["M4"], colors="tab:blue", lw=1.0, zorder=3, label="clk M4"))
ax.add_collection(LineCollection(segs["M5"], colors="tab:orange", lw=1.0, zorder=3, label="clk M5"))
ax.add_collection(LineCollection(segs["lo"], colors="k", lw=1.4, zorder=4, label="clk M2/M3"))
ax.scatter([v[0] for v in vias], [v[1] for v in vias], s=3, c="k", zorder=5, label=f"clk vias {len(vias)}")
taps = [c for c in ck if c[0].endswith("_tap")]
dl = [r[c[0][6:-4]] - g[c[0][6:-4]] for c in taps if c[0][6:-4] in r]
sc = ax.scatter([c[2] for c in taps], [c[3] for c in taps], c=dl, cmap="coolwarm", vmin=-40, vmax=40, s=60, marker="s", edgecolors="k", zorder=6)
others = [c for c in ck if not c[0].endswith("_tap")]
ax.scatter([c[2] for c in others], [c[3] for c in others], s=25, c="lime", edgecolors="k", zorder=6, label="tree nodes")
for c in others:
    if re.fullmatch(r"ot_ms_Q\d_(nd|r\d_nd)|ot_ms_root", c[0]): ax.annotate(c[0][6:], (c[2], c[3]), fontsize=7, zorder=7)
plt.colorbar(sc, ax=ax, shrink=.6, label="leaf tap: RCX - GRT TT leaf-mean arrival (ps)")
ax.set_xlim(0, max(m[2] for m in mac) + 20); ax.set_ylim(0, 216); ax.set_aspect("equal"); ax.legend(loc="upper right", fontsize=8)
ax.set_title(title, fontsize=10); fig.tight_layout(); fig.savefig(out, dpi=100); print(out)
