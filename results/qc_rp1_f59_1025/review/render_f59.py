# PATH-QC-RP1-F59 review render: python3 render_f59.py RDUMP.tsv CKDUMP_TT.tsv MPF_LIST TITLE OUT.png
# (1) whole core: SRAMs, macro-pin IF flops (red), other flops (blue), logic (grey); pin -> nearest connected register
#     (<= 4 levels, reviewer dumpif walk) green <= 20 um, orange <= 40, magenta > 40.
# (2) zoom on the SRAM W pin edges (both banks).
# (3) clock tap panel (TT, GRT RC + measure-basis tap correction): every register coloured by clock arrival; per tap
#     n / mean / min / max, tap-mean window, and each SRAM clock pin vs the mean of its own IF regs (useful skew).
# (4) F6 histogram per pin group (20-um line).
import sys, re, collections, statistics
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.patches as mp
D, CK, MPF, T, O = sys.argv[1:6]
mpf = set(l.strip().replace("\\", "") for l in open(MPF) if l.strip())
die = None; I = []; P = []
for l in open(D):
    f = l.rstrip("\n").split("\t")
    if f[0] == "DIE": die = list(map(float, f[1:5]))
    elif f[0] == "I": I.append((f[1], f[2].replace("\\", ""), *map(float, f[3:7])))
    elif f[0] == "P": P.append((f[1].replace("\\", ""), f[2], int(f[3]), float(f[4]), float(f[5]), float(f[6]), f[7].replace("\\", ""), float(f[8]), float(f[9]), int(f[10])))
def grp(p):
    b = re.sub(r"\[\d+\]$", "", p)
    return {"r_ce_in": "r_addr/r_ce", "r_addr_in": "r_addr/r_ce", "w_ce_in": "w_addr/w_ce", "w_addr_in": "w_addr/w_ce", "wd_in": "wd_in", "rd_out": "rd_out"}.get(b)
P = [p for p in P if grp(p[1])]
CKR = []
for l in open(CK):
    f = l.rstrip("\n").split("\t")
    CKR.append((f[0], f[1].replace("\\", ""), float(f[2]), float(f[3]), float(f[4]), f[5]))
fig, axs = plt.subplots(2, 2, figsize=(24, 22))
mac = [i for i in I if i[0] == "M"]
def draw(ax, lim=None):
    ax.add_patch(mp.Rectangle((die[0], die[1]), die[2]-die[0], die[3]-die[1], fill=False, lw=1))
    for k, n, x0, y0, x1, y1 in mac:
        ax.add_patch(mp.Rectangle((x0, y0), x1-x0, y1-y0, color="#dddddd", ec="k")); ax.text((x0+x1)/2, (y0+y1)/2, n, ha="center", fontsize=9)
    xs = collections.defaultdict(list)
    for k, n, x0, y0, x1, y1 in I:
        if k == "M": continue
        c = "red" if n in mpf else ("tab:blue" if k == "F" else "#bbbbbb")
        xs[c].append(((x0+x1)/2, (y0+y1)/2))
    for c in ("#bbbbbb", "tab:blue", "red"):
        if xs[c]: ax.scatter(*zip(*xs[c]), s=1.5 if c == "#bbbbbb" else 3, c=c, lw=0)
    for p in P:
        col = "green" if p[5] <= 20 else ("orange" if p[5] <= 40 else "magenta")
        ax.plot([p[3], p[7]], [p[4], p[8]], color=col, lw=0.4)
    ax.set_aspect("equal")
    if lim: ax.set_xlim(lim[0], lim[1]); ax.set_ylim(lim[2], lim[3])
    else: ax.set_xlim(die[0]-2, die[2]+2); ax.set_ylim(die[1]-2, die[3]+2)
draw(axs[0][0]); axs[0][0].set_title(T + "\nred = macro-pin IF flops (macro_pin_flops.tcl), blue = other flops; pin->nearest reg (<=4 levels): green <=20, orange <=40, magenta >40 um", fontsize=10)
x0 = min(m[2] for m in mac); y0 = min(m[3] for m in mac); y1 = max(m[5] for m in mac)
draw(axs[0][1], (x0-35, x0+25, y0-8, y1+8)); axs[0][1].set_title("zoom: SRAM W pin edges (both banks)", fontsize=10)
ax = axs[1][0]
F = [r for r in CKR if r[0] == "F"]; Mk = [r for r in CKR if r[0] == "M"]
sc = ax.scatter([r[2] for r in F], [r[3] for r in F], c=[r[4] for r in F], s=4, cmap="viridis", lw=0)
plt.colorbar(sc, ax=ax, fraction=0.04, label="TT clock arrival at CK (ps, GRT RC + tap corr)")
for k, n, a, b, c_, d in mac: ax.add_patch(mp.Rectangle((a, b), c_-a, d-b, fill=False, ec="k"))
taps = collections.defaultdict(list)
for r in F: taps[r[5]].append(r)
lines = []
for t, rs in sorted(taps.items()):
    v = [r[4] for r in rs]; cx = statistics.mean(r[2] for r in rs); cy = statistics.mean(r[3] for r in rs)
    ax.text(cx, cy, t, fontsize=14, weight="bold", color="red")
    lines.append("tap %-4s n %4d mean %6.1f min %6.1f max %6.1f" % (t, len(v), statistics.mean(v), min(v), max(v)))
means = [statistics.mean(r[4] for r in rs) for t, rs in taps.items() if len(rs) > 20]
lines.append("tap-mean window (taps n>20): %.1f ps" % (max(means) - min(means)))
ifb = collections.defaultdict(list)
for p in P:
    if grp(p[1]) != "rd_out": ifb[p[0]].append(p[6])
cka = {r[1]: r for r in CKR}
for m in Mk:
    regs = set(ifb.get(m[1], [])); v = [cka[r][4] for r in regs if r in cka]
    if v: lines.append("SRAM %s clk %.1f | its IF regs n %d mean %.1f -> clk - mean %+.1f ps" % (m[1], m[4], len(v), statistics.mean(v), m[4] - statistics.mean(v)))
    ax.scatter([m[2]], [m[3]], marker="*", s=200, c="red")
ax.text(0.01, -0.02, "\n".join(lines), transform=ax.transAxes, va="top", family="monospace", fontsize=9)
ax.set_aspect("equal"); ax.set_title("clock taps (TT): register clock arrival; red star = SRAM clock pin", fontsize=10)
ax = axs[1][1]
g = collections.defaultdict(list)
for p in P: g[grp(p[1])].append(p[5])
for k, v in sorted(g.items()): ax.hist(v, bins=60, histtype="step", lw=1.5, label="%s n=%d p50 %.1f max %.1f >20: %d" % (k, len(v), statistics.median(v), max(v), sum(x > 20 for x in v)))
ax.axvline(20, color="k", ls="--"); ax.legend(fontsize=10); ax.set_xlabel("SRAM pin -> nearest connected register (um, Manhattan)"); ax.set_yscale("log")
ax.set_title("F6 histogram per SRAM pin group", fontsize=10)
plt.tight_layout(); plt.savefig(O, dpi=100); print("wrote", O); print("\n".join(lines))
