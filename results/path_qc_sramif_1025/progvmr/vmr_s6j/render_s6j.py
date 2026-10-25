# PATH-QC-PROGVMR vmr_s6j (from QC-CQB3 render_s6.py): panels = layout+clock, FF CK, FF hold histogram, SE-region leaf CK s6i vs s6j.
# usage: render_s6j.py DIR TITLE OUT.png LEAF_S6I.tsv LEAF_S6J.tsv
# QC-CQB3 vmr_s6 post-GRT render (after the FF-basis hold repair): python3 render_s6.py DIR TITLE OUT.png
# DIR: dump_tt.tsv dump_ff.tsv ot_macro_pin_flops.txt ot_face_flops.txt s6_hold_hist_{before,after}.tsv [gate.txt]
# Panels: (1) layout + structured clock (taps, trunk, SRAM leaves) + hold buffers; (2) FF clock arrival with the
# SE-tap vm_wdata -> pvm_wdata input region outlined and the near-critical FF hold paths (slack < 20 ps) drawn;
# (3) TT clock arrival; (4) FF hold slack histogram before/after the repair (GRT est, FF basis vclk).
import sys, collections, re, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.patches as mp
D, TITLE, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
LI, LJ = sys.argv[4], sys.argv[5]
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
ports = {U(r[0]): (float(r[1]), float(r[2])) for r in tt["PORT"]}
fig, axs = plt.subplots(1, 4, figsize=(36, 9.8), gridspec_kw={"width_ratios": [1.15, 1.15, 0.9, 1.0]})
def base(ax, t):
    ax.add_patch(mp.Rectangle((die[0], die[1]), die[2] - die[0], die[3] - die[1], fill=False, lw=1))
    for m in macros:
        r = ins[m]; x0, y0, x1, y1 = map(float, r[3:7]); ax.add_patch(mp.Rectangle((x0, y0), x1 - x0, y1 - y0, color="0.88"))
        ax.text((x0 + x1) / 2, (y0 + y1) / 2, m, ha="center", fontsize=8)
    ax.set_xlim(die[0] - 5, die[2] + 5); ax.set_ylim(die[1] - 5, die[3] + 5); ax.set_aspect("equal"); ax.set_title(t, fontsize=9)
regs = [k.rsplit("/", 1)[0] for k in ck["tt"] if k.rsplit("/", 1)[0] not in macros]
hold = [i for i in ins if re.match(r"hold\d+$", i)]
ax = axs[0]
base(ax, f"layout: pin regs green, F6 macro-IF regs blue, other regs grey, hold buffers red dots ({len(hold)}); trunk red, local trees orange, SRAM leaves magenta")
for grp, col in ((set(regs) - pin - mpf, "0.65"), (pin, "g"), (mpf, "b")):
    p = [pos(i) for i in grp if pos(i)]
    if p: ax.scatter(*zip(*p), s=1.2, c=col)
p = [pos(i) for i in hold if pos(i)]
if p: ax.scatter(*zip(*p), s=1.5, c="r")
ax.scatter(*zip(*ports.values()), s=1, c="k")
drivers = set(d for _, d, _ in cn)
for net, drv, sinks in cn:
    if drv.startswith("PORT:") or drv not in ins: continue
    a = pos(drv)
    trunk = net.startswith("ot_ms_") and not re.match(r"ot_ms_(SW|SE\w*|W0|W1|E\w*)_clk$", net)
    for s in sinks:
        si = s.rsplit("/", 1)[0]; b = pos(si)
        if not b: continue
        if si.startswith("ot_ms_m") or net.startswith("ot_ms_m") or si in macros: ax.plot([a[0], b[0]], [a[1], b[1]], c="m", lw=1.2)
        elif trunk and si.startswith("ot_ms_"): ax.plot([a[0], b[0]], [a[1], b[1]], c="r", lw=1.4)
        elif si in drivers: ax.plot([a[0], b[0]], [a[1], b[1]], c="orange", lw=0.5)
for t in [i for i in ins if re.match(r"ot_ms_\w+_tap$", i)]:
    q = pos(t); ax.plot(*q, "r*", ms=14); ax.text(q[0] + 2, q[1] + 3, t[6:-4], color="r", fontsize=10, weight="bold")
for l in [i for i in ins if re.match(r"ot_ms_m\d+_leaf$", i)]:
    q = pos(l); ax.plot(*q, "m^", ms=9)
r = pos("ot_ms_root")
if r: ax.plot(*r, "ks", ms=8); ax.text(r[0] + 2, r[1] - 4, "root", fontsize=8)
# vm_wdata -> pvm_wdata region
pv = [pos(i) for i in regs if i.startswith("pvm_wdata") and pos(i)]
vp = [v for k, v in ports.items() if k.startswith("vm_wdata")]
def box(ax, pts, col, lab):
    if not pts: return
    xs, ys = zip(*pts); ax.add_patch(mp.Rectangle((min(xs) - 2, min(ys) - 2), max(xs) - min(xs) + 4, max(ys) - min(ys) + 4, fill=False, ec=col, lw=1.6, ls="--"))
    ax.text(min(xs), max(ys) + 4, lab, color=col, fontsize=9, weight="bold")
for k, c in ((1, "ff"),):
    ax = axs[k]; d = ck[c]; ks = [x for x in d if pos(x.rsplit("/", 1)[0])]
    sc = ax.scatter([pos(x.rsplit("/", 1)[0])[0] for x in ks], [pos(x.rsplit("/", 1)[0])[1] for x in ks], c=[d[x] for x in ks], s=3, cmap="viridis")
    plt.colorbar(sc, ax=ax, fraction=0.04)
    wn = (ff if c == "ff" else tt)["WNS"][0]
    base(ax, f"{c.upper()} clock arrival (ps, GRT RC-cal + per-tap RCX corr) | hold WNS {float(wn[0]):.2f} ep {wn[1]} | setup WNS {float(wn[2]):.2f}")
    for m in macros:
        a = d.get(m + "/clk"); q = pos(m)
        if a is not None: ax.text(q[0], q[1] - 12, f"clk {a:.1f}", ha="center", fontsize=9, color="m")
    box(ax, pv, "r", f"pvm_wdata regs ({len(pv)})"); box(ax, vp, "k", "vm_wdata ports")
    pw = [pos(i) for i in regs if i.startswith("pw16_data") and pos(i)]; box(ax, pw, "m", f"pw16_data pin regs ({len(pw)})")
    lw = [pos(i) for i in regs if i.startswith("l_w16d") and pos(i)]; box(ax, lw, "c", f"l_w16d landing ({len(lw)})")
    if c == "ff":
        nh = 0
        for h in ff["HOLD"]:
            ep, sp, sl = U(h[0]), U(h[1]), float(h[2])
            a = ports.get(sp) or pos(sp.rsplit("/", 1)[0]); b = ports.get(ep) or pos(ep.rsplit("/", 1)[0])
            if a and b:
                ax.plot([a[0], b[0]], [a[1], b[1]], c="r" if sl < 5 else "orange", lw=0.6, alpha=0.7); nh += 1
        ax.text(die[0], die[1] - 4, f"{nh} FF hold paths with slack < 20 ps drawn (red < 5 ps)", fontsize=9, color="r")
ax = axs[2]
for fn, col, lab in (("s6_hold_hist_before.tsv", "0.6", "before repair"), ("s6_hold_hist_after.tsv", "tab:blue", "after repair")):
    f = f"{D}/{fn}"
    if not os.path.exists(f): continue
    rows = [l.split("\t") for l in open(f).read().split("\n")[1:] if l.strip()]
    ax.bar([int(r[0]) + 2.5 for r in rows], [int(r[1]) for r in rows], width=4.5, color=col, alpha=0.7, label=lab)
ax.axvline(0, c="r", lw=1); ax.set_yscale("log"); ax.set_xlabel("FF hold slack, ps (5 ps bins, endpoints with slack < 100 ps)")
ax.set_ylabel("endpoints"); ax.legend(); ax.set_title("FF hold slack histogram, FF-basis vclk (GRT estimate)", fontsize=9)
txt = open(f"{D}/gate.txt").read() if os.path.exists(f"{D}/gate.txt") else ""
ax = axs[3]
def leafs(fn):
    out = []
    for l in open(fn).read().split("\n")[1:]:
        t = l.split("\t")
        if len(t) < 6: continue
        m = re.match(r"clkbuf_leaf_\d+_ot_ms_(\w+)_clk", t[0])
        if not m or not m.group(1).startswith("SE"): continue
        x, y = map(float, t[1].split()); out.append((x, float(t[3]), float(t[4]), float(t[5]), m.group(1)))
    return out
for fn, col, lab in ((LI, "tab:red", "s6i single SE tap"), (LJ, "tab:blue", "s6j SEa + SEb")):
    L = leafs(fn)
    if not L: continue
    ax.errorbar([l[0] for l in L], [l[1] for l in L], yerr=[[l[1] - l[2] for l in L], [l[3] - l[1] for l in L]], fmt="o", ms=3, c=col, label=f"{lab}: leaves {len(L)}, FF CK {min(l[2] for l in L):.1f}..{max(l[3] for l in L):.1f} ({max(l[3] for l in L) - min(l[2] for l in L):.1f} ps)")
ax.set_xlabel("leaf buffer x (um), SE region x 110-260"); ax.set_ylabel("FF clock arrival at leaf sinks (ps; mean, min..max)")
ax.legend(fontsize=8); ax.set_title("SE-region local trees: per-leaf FF CK, s6i vs s6j (same 3_place)", fontsize=9)
fig.suptitle(TITLE + ("\n" + txt if txt else ""), fontsize=10)
plt.tight_layout(); plt.savefig(OUT, dpi=95)
print("ok", OUT)
