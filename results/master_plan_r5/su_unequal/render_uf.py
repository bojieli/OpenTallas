import json, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
fig, axs = plt.subplots(1, len(sys.argv) - 2, figsize=(5.5 * (len(sys.argv) - 2), 7), dpi=110)
for ax, (geo, js) in zip(axs, [a.split(",") for a in sys.argv[2:]]):
    R = json.load(open(js)); b = R["best"]
    S = []
    for l in open(geo):
        f = l.split()
        if not f: continue
        if f[0] == "CORE": cr = list(map(float, f[1:5]))
        if f[0] == "MACRO":
            r = list(map(float, f[3:7])); ax.add_patch(Rectangle((r[0], r[1]), r[2]-r[0], r[3]-r[1], fc="#9fb7d6"))
        if f[0] == "SINK": S.append((float(f[1]), float(f[2])))
    ax.add_patch(Rectangle((cr[0], cr[1]), cr[2]-cr[0], cr[3]-cr[1], fill=False))
    ax.plot([p[0] for p in S], [p[1] for p in S], ",", color="#888")
    e = R["entry"]
    for q, isl in enumerate(b["islands"]):
        ax.plot([e[0], isl[0]], [e[1], isl[1]], "-", color="#c0392b", lw=1.5)
        for k, v in b["B_sites"].items():
            if k.startswith(f"Q{q}B"):
                ax.plot([isl[0], v[0]], [isl[1], v[1]], "-", color="#e67e22", lw=1)
                for kl, lv in b["leaf_sites"].items():
                    if kl.startswith(k + "L"):
                        ax.plot([v[0], lv[0]], [v[1], lv[1]], "-", color="#27ae60", lw=0.6)
        ax.plot(*isl, "s", ms=9, color="#c0392b"); ax.annotate(f"Q{q}:{b['island_sinks'][q]}", isl, fontsize=8)
    ax.plot(*e, "*", ms=14, color="k")
    t, f_ = b["pred"]["TT"], b["pred"]["FF"]
    ax.set_title(f"{geo.split('/')[-1]} k={b['k']} B/isl={b['B_per_island']}\nmodel TT {t['mean']}/{t['window']} FF {f_['mean']}/{f_['window']} (raw NLDM, no offset)", fontsize=8)
    ax.set_aspect("equal")
fig.tight_layout(); fig.savefig(sys.argv[1])
