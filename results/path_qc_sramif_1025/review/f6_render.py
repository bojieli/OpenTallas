# PATH-QC-SRAMIF F6 render: python3 f6_render.py DUMP.tsv TITLE OUT.png [mpf_list]
# Panel 1: layout (macros, macro-pin flops red, other flops blue, logic grey) + pin->register links coloured by distance.
# Panel 2: zoom on the SRAM pin edges.  Panel 3: distance histogram per pin group (20-um line).
import sys, re, collections
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.patches as mp
D, T, O = sys.argv[1], sys.argv[2], sys.argv[3]
mpf = set(l.strip().replace("\\", "") for l in open(sys.argv[4])) if len(sys.argv) > 4 else set()
die = None; I = []; P = []
for l in open(D):
    f = l.rstrip("\n").split("\t")
    if f[0] == "DIE": die = list(map(float, f[1:5]))
    elif f[0] == "I": I.append((f[1], f[2].replace("\\", ""), *map(float, f[3:7])))
    elif f[0] == "P": P.append((f[1].replace("\\", ""), f[2], int(f[3]), float(f[4]), float(f[5]), float(f[6]), f[7], float(f[8]), float(f[9]), int(f[10])))
def grp(p):
    b = re.sub(r"\[\d+\]$", "", p)
    return {"r_ce_in": "r_addr/r_ce", "r_addr_in": "r_addr/r_ce", "w_ce_in": "w_addr/w_ce", "w_addr_in": "w_addr/w_ce", "wd_in": "wd_in", "rd_out": "rd_out"}.get(b)
P = [p for p in P if grp(p[1])]
fig, axs = plt.subplots(1, 3, figsize=(30, 11), gridspec_kw={"width_ratios": [1, 1, 0.8]})
mac = [i for i in I if i[0] == "M"]
def draw(ax, lim=None):
    ax.add_patch(mp.Rectangle((die[0], die[1]), die[2]-die[0], die[3]-die[1], fill=False, lw=1))
    for k, n, x0, y0, x1, y1 in I:
        if k == "M": ax.add_patch(mp.Rectangle((x0, y0), x1-x0, y1-y0, color="#bbbbbb", ec="k")); ax.text((x0+x1)/2, (y0+y1)/2, n, ha="center", fontsize=8)
    xs = collections.defaultdict(list)
    for k, n, x0, y0, x1, y1 in I:
        if k == "M": continue
        c = "red" if n in mpf else ("tab:blue" if k == "F" else "#cccccc")
        xs[c].append(((x0+x1)/2, (y0+y1)/2))
    for c in ("#cccccc", "tab:blue", "red"):
        if xs[c]: ax.scatter(*zip(*xs[c]), s=1 if c == "#cccccc" else 2, c=c, lw=0)
    for p in P:
        col = "green" if p[5] <= 20 else ("orange" if p[5] <= 40 else "magenta")
        ax.plot([p[3], p[7]], [p[4], p[8]], color=col, lw=0.3)
    ax.set_aspect("equal")
    if lim: ax.set_xlim(lim[0], lim[1]); ax.set_ylim(lim[2], lim[3])
draw(axs[0]); axs[0].set_title(T + "\nred = macro-pin (IF) flops, blue = other flops; links pin->nearest reg (<=4 levels): green <=20, orange <=40, magenta >40 um", fontsize=9)
m0 = mac[0]; draw(axs[1], (m0[2]-30, m0[2]+40, m0[3]-5, m0[5]+5)); axs[1].set_title("zoom: %s W pin edge" % m0[1], fontsize=9)
g = collections.defaultdict(list)
for p in P: g[grp(p[1])].append(p[5])
for k, v in sorted(g.items()): axs[2].hist(v, bins=60, histtype="step", label="%s n=%d max %.1f >20: %d" % (k, len(v), max(v), sum(x > 20 for x in v)))
axs[2].axvline(20, color="k", ls="--"); axs[2].legend(fontsize=9); axs[2].set_xlabel("pin -> nearest connected register (um, Manhattan)"); axs[2].set_yscale("log")
plt.tight_layout(); plt.savefig(O, dpi=110); print("wrote", O)
