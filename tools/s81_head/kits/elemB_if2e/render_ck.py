"""PATH-S81/ELEMB: render clock arrival per sink (ckdump2 ck_<c>.tsv, GRT RC) + taps + ROM IF regs + FF hold endpoints."""
import sys, re, collections
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
tsv, holdend, png, title = sys.argv[1:5]
R = []; B = []; M = []
for ln in open(tsv):
    p = ln.rstrip("\n").split("\t")
    if len(p) < 6 or p[5] in ("NA", ""): continue
    k, n, m, x, y, a = p[0], p[1].replace(chr(92), ""), p[2], float(p[3]), float(p[4]), float(p[5])
    anc = p[7].split(",") if len(p) > 7 else []
    tap = next((t for t in anc if t.startswith("ot_dtap_")), "")
    (R if k == "REG" else M if k == "MAC" else B).append((n, x, y, a, tap))
hold = set()
for ln in open(holdend):
    q = ln.split()
    if len(q) >= 5 and q[-1] == "(VIOLATED)" and "/" in q[0]: hold.add(q[0].rsplit("/", 1)[0])
fig, axs = plt.subplots(1, 2, figsize=(20, 10))
ax = axs[0]
xs = [r[1] for r in R]; ys = [r[2] for r in R]; cs = [r[3] for r in R]
lo, hi = sorted(cs)[int(.01*len(cs))], sorted(cs)[int(.99*len(cs))]
sc = ax.scatter(xs, ys, c=cs, s=0.6, cmap="viridis", vmin=lo, vmax=hi, linewidths=0)
fig.colorbar(sc, ax=ax, label="CK arrival ps")
taps = [b for b in B if re.match(r"ot_dtap_\d+$", b[0])]
ax.scatter([t[1] for t in taps], [t[2] for t in taps], marker="^", s=40, c="r", label=f"taps {len(taps)}")
for t in taps: ax.annotate(t[0][8:], (t[1], t[2]), fontsize=6, color="r")
for n, x, y, a, tap in M:
    ax.annotate(n.split(".")[-1] + f" CK {a:.0f} ({tap})", (x, y), fontsize=9, color="m", weight="bold")
    ax.plot([x], [y], "ms", ms=8)
for r in (0, 1):
    pts = [q for q in R if re.match(rf"u_m\.(cap{r}|u_rom_addr{r}/addr)", q[0])]
    if pts:
        ax.scatter([q[1] for q in pts], [q[2] for q in pts], s=4, facecolors="none", edgecolors="m" if r == 0 else "c", linewidths=0.4, label=f"rom{r} IF regs {len(pts)} mean {sum(q[3] for q in pts)/len(pts):.1f}")
ax.set_aspect("equal"); ax.legend(fontsize=7, loc="upper right"); ax.set_title(title + " | CK arrival", fontsize=9)
ax = axs[1]
ax.scatter(xs, ys, c="0.85", s=0.3, linewidths=0)
hp = [r for r in R if r[0] in hold]
ax.scatter([r[1] for r in hp], [r[2] for r in hp], c="r", s=2, label=f"hold-violating capture regs {len(hp)}")
ax.set_aspect("equal"); ax.legend(fontsize=7); ax.set_title(title + " | hold endpoints", fontsize=9)
fig.savefig(png, dpi=110, bbox_inches="tight")
bt = collections.defaultdict(list)
for r in R: bt[r[4]].append(r[3])
print("taps", len(taps), "regs", len(R), "tap mean min/max", min(sum(v)/len(v) for v in bt.values()), max(sum(v)/len(v) for v in bt.values()), "hold regs", len(hp))
