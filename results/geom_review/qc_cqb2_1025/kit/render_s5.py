# QC-CQB2 s5 render (post-CTS/GRT or routed): python3 render_s5.py DIR TITLE OUT.png  (DIR: dump_tt.tsv dump_ff.tsv
# ot_macro_pin_flops.txt ot_face_flops.txt [gate.txt]).  Derived from the QC-CQB render.py.
import sys, collections, statistics as S, re, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.patches as mp
D, TITLE, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
U = lambda s: s.replace("\\", "")
def load(c):
    d = collections.defaultdict(list)
    for l in open(f"{D}/dump_{c}.tsv"):
        t = l.rstrip("\n").split("\t"); d[t[0]].append(t[1:])
    return d
tt, ff = load("tt"), load("ff")
ins = {U(r[0]): r for r in tt["INST"]}
macros = [U(r[0]) for r in tt["INST"] if r[2] == "macro"]
def pos(i):
    r = ins.get(i); return ((float(r[3]) + float(r[5])) / 2, (float(r[4]) + float(r[6])) / 2) if r else None
ck = {c: {U(r[0]): float(r[1]) for r in d["CK"] if r[1]} for c, d in (("tt", tt), ("ff", ff))}
mpf = set(U(l.split("\t")[0].strip()) for l in open(f"{D}/ot_macro_pin_flops.txt") if l.strip())
pin = set(U(l.split("\t")[0].strip()) for l in open(f"{D}/ot_face_flops.txt") if l.strip())
cn = [(U(r[0]), U(r[1]), [U(s) for s in r[3].split()] if len(r) > 3 else []) for r in tt["CNET"]]
die = [float(x) for x in tt["DIE"][0]]
fig, axs = plt.subplots(1, 3, figsize=(27, 9.6))
def base(ax, t):
    ax.add_patch(mp.Rectangle((die[0], die[1]), die[2] - die[0], die[3] - die[1], fill=False, lw=1))
    for m in macros:
        r = ins[m]; x0, y0, x1, y1 = map(float, r[3:7]); ax.add_patch(mp.Rectangle((x0, y0), x1 - x0, y1 - y0, color="0.88"))
        ax.text((x0 + x1) / 2, (y0 + y1) / 2, m, ha="center", fontsize=8)
    ax.set_xlim(die[0] - 5, die[2] + 5); ax.set_ylim(die[1] - 5, die[3] + 5); ax.set_aspect("equal"); ax.set_title(t, fontsize=9)
regs = [k.rsplit("/", 1)[0] for k in ck["tt"] if k.rsplit("/", 1)[0] not in macros]
ax = axs[0]
base(ax, "layout: pin regs green, F6 macro-interface regs blue, other regs grey; trunk red (root->stages->taps), local CTS trees orange, macro leaves magenta")
for grp, col in ((set(regs) - pin - mpf, "0.65"), (pin, "g"), (mpf, "b")):
    p = [pos(i) for i in grp if pos(i)]
    if p: ax.scatter(*zip(*p), s=1.2, c=col)
px = [(float(r[1]), float(r[2])) for r in tt["PORT"]]; ax.scatter(*zip(*px), s=1, c="k")
drivers = set(d for _, d, _ in cn)
for net, drv, sinks in cn:
    if drv.startswith("PORT:") or drv not in ins: continue
    a = pos(drv)
    trunk = net.startswith("ot_ms_") and not re.match(r"ot_ms_(SW|SE|W0|W1|E\w*)_clk$", net)
    for s in sinks:
        si = s.rsplit("/", 1)[0]
        b = pos(si)
        if not b: continue
        if si in macros and s.endswith("/clk"):
            r = ins[si]; b = (float(r[3]), float(r[4]) + 0.78)  # LEF clk pin: left edge, y 0.78 (R0)
        if si.startswith("ot_ms_m") or net.startswith("ot_ms_m") or si in macros:
            ax.plot([a[0], b[0]], [a[1], b[1]], c="m", lw=1.2)
        elif trunk and si.startswith("ot_ms_"):
            ax.plot([a[0], b[0]], [a[1], b[1]], c="r", lw=1.4)
        elif si in drivers:
            ax.plot([a[0], b[0]], [a[1], b[1]], c="orange", lw=0.5)
taps = [i for i in ins if re.match(r"ot_ms_\w+_tap$", i)]
for t in taps:
    p = pos(t); ax.plot(*p, "r*", ms=14); ax.text(p[0] + 2, p[1] + 3, t[6:-4], color="r", fontsize=10, weight="bold")
for l in [i for i in ins if re.match(r"ot_ms_m\d+_leaf$", i)]:
    p = pos(l); ax.plot(*p, "m^", ms=9)
r = pos("ot_ms_root"); ax.plot(*r, "ks", ms=8); ax.text(r[0] + 2, r[1] - 4, "root", fontsize=8)
for k, c in ((1, "tt"), (2, "ff")):
    ax = axs[k]
    d = ck[c]; ks = [x for x in d if pos(x.rsplit("/", 1)[0])]
    sc = ax.scatter([pos(x.rsplit("/", 1)[0])[0] for x in ks], [pos(x.rsplit("/", 1)[0])[1] for x in ks], c=[d[x] for x in ks], s=3, cmap="viridis")
    plt.colorbar(sc, ax=ax, fraction=0.04)
    base(ax, f"{c.upper()} clock arrival at register / macro clock pins (ps), {TITLE.split('|')[-1].strip()}")
    for m in macros:
        a = d.get(m + "/clk"); q = pos(m)
        if a is not None: ax.text(q[0], q[1] - 12, f"clk {a:.1f}", ha="center", fontsize=9, color="m")
txt = ""
if os.path.exists(f"{D}/gate.txt"): txt = open(f"{D}/gate.txt").read()
fig.suptitle(TITLE + ("\n" + txt if txt else ""), fontsize=10)
plt.tight_layout(); plt.savefig(OUT, dpi=105)
print("ok", OUT)
