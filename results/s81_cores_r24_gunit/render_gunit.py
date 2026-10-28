import json, sys, re, collections
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
B = sys.argv[1]; out = sys.argv[2]; cfgs = json.loads(sys.argv[3])
d = json.load(open(B + "/die_plan.json")); pt = d["partition_types"]["gunit__t1"]
cores = {c["inst"].split(".")[-1]: c for c in pt["hard_cores"]}
fig, axs = plt.subplots(1, len(cfgs), figsize=(9 * len(cfgs), 5.5))
for ax, (title, res, moves) in zip(axs, cfgs):
    r = json.load(open(res))["bundles"]
    org = {i: moves.get(i, c["origin_um"]) for i, c in cores.items()}
    for i, c in cores.items():
        x, y = org[i]; w, h = c["outline_um"]
        ax.add_patch(plt.Rectangle((x, y), w, h, fill=True, alpha=0.25, ec="k", fc="tab:blue" if i not in moves else "tab:orange"))
        ax.text(x + w / 2, y + h / 2, i[2:], ha="center", va="center", fontsize=8)
    for k, v in r.items():
        a, b = k.split("-")
        ca = (org[a][0] + cores[a]["outline_um"][0] / 2, org[a][1] + cores[a]["outline_um"][1] / 2)
        cb = (org[b][0] + cores[b]["outline_um"][0] / 2, org[b][1] + cores[b]["outline_um"][1] / 2)
        col = "red" if v["gt405"] else "green"
        ax.plot([ca[0], cb[0]], [ca[1], cb[1]], color=col, lw=2)
        ax.text((ca[0] + cb[0]) / 2, (ca[1] + cb[1]) / 2, "%s-%s max %.0f\n>405 %d/%d" % (a[2:], b[2:], v["max"], v["gt405"], v["bits"]), fontsize=6, color=col)
    ax.set_xlim(600, 2100); ax.set_ylim(0, 1000); ax.set_aspect("equal"); ax.set_title(title, fontsize=9)
plt.tight_layout(); plt.savefig(out, dpi=110)
