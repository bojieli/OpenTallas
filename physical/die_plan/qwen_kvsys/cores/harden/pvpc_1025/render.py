import json, sys, numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
d = json.load(open(sys.argv[1])); out = sys.argv[2]
W, H = 380.16, 190.08
fig, ax = plt.subplots(figsize=(19, 10.5))
I = d["insts"]
for k, c, s in (("std", "#bbbbbb", 0.3), ("buf", "#88aaff", 0.3), ("ff", "#66bb66", 0.3)):
    xs = [r[2] for r in I if r[0] == k]; ys = [r[3] for r in I if r[0] == k]
    ax.scatter(xs, ys, s=s, c=c, lw=0, label=f"{k} {len(xs)}")
for r in I:
    if r[0] == "macro":
        ax.add_patch(plt.Rectangle((r[2], r[3]), r[4], r[5], fc="#ffe0a0", ec="k", lw=0.8)); ax.text(r[2]+1, r[3]+1, r[1][-28:], fontsize=6)
bc = [p for p in d["pins"] if "bc" in p[0]]; clk = [p for p in d["pins"] if "clk" in p[0]]
oth = [p for p in d["pins"] if p not in bc and p not in clk]
ax.scatter([p[1] for p in oth], [p[2] for p in oth], s=3, c="purple", label=f"pins {len(oth)}")
ax.scatter([p[1] for p in bc], [p[2] for p in bc], s=25, c="orange", marker="s", label="bc (control) pins")
for p in clk: ax.scatter(p[1], p[2], s=200, c="red", marker="*"); ax.text(p[1]+2, p[2]-6, p[0], color="red", fontsize=9)
P = d["path"]; pts = [(n, v) for n, v in P.items() if v]
ax.plot([v["x"] for n, v in pts if not n.startswith(("wire1515", "clkbuf"))], [v["y"] for n, v in pts if not n.startswith(("wire1515", "clkbuf"))], "r-o", ms=4, lw=1.5, label="worst TT setup path c_r[17] -> g_lane[2] rd[91] (-40.94)")
ax.plot([v["x"] for n, v in pts if n.startswith(("wire15158", "wire15157", "clkbuf"))], [v["y"] for n, v in pts if n.startswith(("wire15158", "wire15157", "clkbuf"))], "m--s", ms=6, lw=1.5, label="clock trunk pin -> clkbuf_regs_0")
a = P.get("_113867_")
if a:
    for pin, (net, fo, loc) in a["fo"].items():
        ax.scatter([l[0] for l in loc], [l[1] for l in loc], s=6, c="red", marker="x", label=f"AO21x1 {net} fanout {fo}")
ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_aspect("equal"); ax.legend(loc="upper right", fontsize=7, markerscale=3)
ax.set_title(sys.argv[3], fontsize=10)
plt.savefig(out, dpi=90, bbox_inches="tight")
