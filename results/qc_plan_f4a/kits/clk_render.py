import sys, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
out = sys.argv[1]; pairs = sys.argv[2:]
fig, axs = plt.subplots(1, len(pairs) // 2, figsize=(11 * len(pairs) // 2, 10))
for ax, (title, fn) in zip(axs, zip(pairs[::2], pairs[1::2])):
    ff, ck, mac = [], [], []
    for l in open(fn):
        f = l.split()
        if f[0] == "FF": ff.append((float(f[1]), float(f[2])))
        elif f[0] == "CKBUF": ck.append((f[1], f[2], float(f[3]), float(f[4])))
        elif f[0] == "MACRO": mac.append(tuple(map(float, f[2:6])))
    for r in mac: ax.add_patch(plt.Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], color="0.75"))
    ax.scatter([p[0] for p in ff], [p[1] for p in ff], s=1, c="tab:blue", alpha=.4, label=f"flops {len(ff)}")
    for c in ck:
        big = "x16" in c[1] or "x24" in c[1]
        ax.scatter([c[2]], [c[3]], s=40 if big else 12, c="red" if big else "tab:green", marker="s" if big else "o")
    ax.set_xlim(0, 250.56); ax.set_ylim(0, 216); ax.set_aspect("equal")
    ax.set_title(f"{title}: 5_1_grt clock cells {len(ck)} (red = x16/x24 trunk/root), grey = column SRAM")
    ax.legend(loc="upper right")
fig.tight_layout(); fig.savefig(out, dpi=110)
print(out)
