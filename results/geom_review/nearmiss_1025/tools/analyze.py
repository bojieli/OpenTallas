#!/usr/bin/env python3
"""NEARMISS-STRUCT routed-run review: renders + structural metrics from probe dumps (dump_tt/ff.tsv, ckest_tt.tsv, route.guide).
usage: analyze.py <dir> <title> [route.guide]"""
import sys, collections, statistics as S, json, math
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.patches as mp, numpy as np
D, title = sys.argv[1], sys.argv[2]; guide = sys.argv[3] if len(sys.argv) > 3 else None
U = lambda s: s.replace("\\", "")
def load(c):
    d = collections.defaultdict(list)
    for l in open(f"{D}/dump_{c}.tsv"):
        t = l.rstrip("\n").split("\t"); d[t[0]].append(t[1:])
    return d
ff, tt = load("ff"), load("tt")
ins = {U(r[0]): r for r in ff["INST"]}
macros = [U(r[0]) for r in ff["INST"] if r[2] == "macro"]
def ckd(d): return {U(r[0]): float(r[1]) for r in d["CK"] if len(r) > 1 and r[1] not in ("", "INF", "-INF")}
ck, ckt = ckd(ff), ckd(tt)
est = {}
try:
    for l in open(f"{D}/ckest_tt.tsv"):
        t = l.rstrip("\n").split("\t")
        if t[0] == "CK" and len(t) > 2 and t[2] not in ("", "INF", "-INF"): est[U(t[1])] = float(t[2])
except FileNotFoundError: pass
inst = lambda p: p.rsplit("/", 1)[0]
def pos(i):
    r = ins.get(i)
    return ((float(r[3]) + float(r[5])) / 2, (float(r[4]) + float(r[6])) / 2) if r else None
ports = {U(r[0]): (float(r[1]), float(r[2])) for r in ff["PORT"]}
def portpos(p):
    return ports.get(U(p)) or ports.get(U(p).replace("[", "\\[").replace("]", "\\]"))
ckpin = {}
for k in ck: ckpin.setdefault(inst(k), k)
def arr(i, d):
    k = ckpin.get(i); return d.get(k) if k else None
p2r = [(r[0], U(r[1]), U(r[2])) for r in ff["P2R"]]
pinreg = set(x[2] for x in p2r)
man = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])
die = [float(x) for x in ff["DIE"][0]]
out = dict(title=title, die_um=[die[2] - die[0], die[3] - die[1]], cells=len(ins), macros=len(macros))
# pin -> register distance
dist = collections.defaultdict(list); farp = []
for d_, p, r in p2r:
    a, b = portpos(p), pos(r)
    if a and b:
        dist[d_].append(man(a, b)); farp.append((man(a, b), d_, p, r))
for d_ in dist:
    v = sorted(dist[d_]); out[f"p2r_{d_}"] = dict(n=len(v), p90=round(v[int(.9 * (len(v) - 1))], 1), max=round(v[-1], 1))
out["p2r_far"] = [(round(x[0], 1), x[1], x[2], x[3]) for x in sorted(farp, reverse=True)[:5]]
# insertion
def stat(v):
    v = [x for x in v if x is not None]
    return dict(n=len(v), mean=round(S.mean(v), 1), min=round(min(v), 1), max=round(max(v), 1)) if v else None
out["I_pinreg_tt"] = stat([arr(i, ckt) for i in pinreg]); out["I_pinreg_ff"] = stat([arr(i, ck) for i in pinreg])
out["I_all_ff"] = stat(list(ck.values()))
if est:
    dd = [est[k] - ckt[k] for k in ckt if k in est]
    out["grt_minus_rcx_tt"] = stat(dd)
    out["I_pinreg_tt_grt_est"] = stat([est.get(ckpin.get(i)) for i in pinreg])
# macro interface registers
mif = collections.defaultdict(list)
for d_, pn, r in ((x[0], U(x[1]), U(x[2])) for x in ff["MIF"]):
    m = pn.split("/")[0] if pn.split("/")[0] in macros else inst(pn)
    if pos(r): mif[m].append((d_, pn, r))
out["macro_if"] = {}
for m, L in mif.items():
    r0 = ins[m]; x0, y0, x1, y1 = map(float, r0[3:7])
    def dbox(p): return max(x0 - p[0], 0, p[0] - x1) + max(y0 - p[1], 0, p[1] - y1)
    ds = sorted(dbox(pos(r)) for _, _, r in L)
    mck = arr(m, ck); rck = [arr(r, ck) for _, _, r in L if arr(r, ck) is not None]
    out["macro_if"][m] = dict(n=len(L), dist_to_macro_p50=round(ds[len(ds) // 2], 1), p90=round(ds[int(.9 * (len(ds) - 1))], 1), max=round(ds[-1], 1),
                             macro_clk_ff=mck, if_reg_clk_ff_mean=round(S.mean(rck), 1) if rck else None,
                             macro_minus_ifreg_ps=round(mck - S.mean(rck), 1) if (mck and rck) else None)
def kind(i):
    if i in macros or inst(i) in macros: return "macro"
    if i.startswith("PORT") or i not in ckpin: return "port"
    return "pinreg" if i in pinreg else "internal"
def viol(d, tag):
    rows = []
    for r in d[tag]:
        ep, sp, sl = U(r[0]), U(r[1]), float(r[2])
        ei, si = inst(ep), inst(sp)
        if si not in ins and portpos(sp): si = "PORT:" + sp
        if ei not in ins and portpos(ep): ei = "PORT:" + ep
        a = pos(si) if not si.startswith("PORT:") else portpos(sp)
        b = pos(ei) if not ei.startswith("PORT:") else portpos(ep)
        rows.append(dict(sl=sl, ep=ep, sp=sp, ek=kind(ei), sk=kind(si), lck=arr(si, ck if tag == "HOLD" else ckt), cck=arr(ei, ck if tag == "HOLD" else ckt),
                         a=a, b=b, d=man(a, b) if a and b else None, npts=int(r[6]) if len(r) > 6 else None,
                         lest=est.get(ckpin.get(si)), cest=est.get(ckpin.get(ei))))
    return rows
H, St = viol(ff, "HOLD"), viol(tt, "SETUP")
for tag, rows in (("hold_ff", H), ("setup_tt", St)):
    o = dict(n=len(rows))
    if rows:
        o["wns"] = min(r["sl"] for r in rows)
        o["classes"] = collections.Counter(f"{r['sk']}->{r['ek']}" for r in rows).most_common(6)
        sk = [r["cck"] - r["lck"] for r in rows if r["cck"] is not None and r["lck"] is not None]
        if sk: o["skew_capture_minus_launch"] = stat(sk)
        dd = [r["d"] for r in rows if r["d"] is not None]
        if dd: o["dist_um"] = stat(dd)
        se = [(r["cck"] - r["lck"]) - (r["cest"] - r["lest"]) for r in rows if None not in (r["cck"], r["lck"], r["cest"], r["lest"])]
        if se and tag == "hold_ff": o["skew_rcx_minus_grtest_tt_basis"] = stat(se)
        o["worst"] = [dict(sl=round(r["sl"], 2), sp=r["sp"], ep=r["ep"], cls=f"{r['sk']}->{r['ek']}", skew=None if None in (r["cck"], r["lck"]) else round(r["cck"] - r["lck"], 1), d=None if r["d"] is None else round(r["d"], 1), npts=r["npts"]) for r in sorted(rows, key=lambda r: r["sl"])[:8]]
        o["ep_groups"] = collections.Counter(r["ep"].split("/")[0].split("[")[0].split(".")[0] for r in rows).most_common(8)
        o["sp_groups"] = collections.Counter(r["sp"].split("/")[0].split("[")[0].split(".")[0] for r in rows).most_common(8)
    out[tag] = o
# clock tree
cnets = [(U(r[1]), [U(s) for s in r[3].split()] if len(r) > 3 else []) for r in ff["CNET"]]
drv = set(d for d, _ in cnets)
roots = [d for d, _ in cnets if d.startswith("PORT:")]
out["clock_nets"] = len(cnets); out["clock_root"] = roots
# guide density
gd = None
if guide:
    try:
        xs = []; xmax = 0
        G = 60; gx = np.zeros((G, G))
        lines = open(guide).read().split("\n")
        rects = [l.split() for l in lines if l and l[0].isdigit()]
        mx = max(int(r[2]) for r in rects); my = max(int(r[3]) for r in rects)
        dbu = round(max(mx / max(die[2], 1), my / max(die[3], 1)))
        # snap dbu to a power of ten-ish standard
        for c in (1000, 2000, 4000): 
            if abs(dbu - c) / c < .3: dbu = c
        for r in rects:
            if r[4] in ("M1",): continue
            x0, y0, x1, y1 = (int(v) / dbu for v in r[:4])
            i0, i1 = int(x0 / die[2] * G), int(min(x1 / die[2], .9999) * G)
            j0, j1 = int(y0 / die[3] * G), int(min(y1 / die[3], .9999) * G)
            gx[j0:j1 + 1, i0:i1 + 1] += (x1 - x0) + (y1 - y0)
        gd = gx
    except Exception as e:
        out["guide_err"] = str(e)
# --- render ---
fig, axs = plt.subplots(2, 3, figsize=(27, 17))
def base(ax, t):
    ax.add_patch(mp.Rectangle((die[0], die[1]), die[2] - die[0], die[3] - die[1], fill=False, lw=1))
    for m in macros:
        r = ins[m]; x0, y0, x1, y1 = map(float, r[3:7]); ax.add_patch(mp.Rectangle((x0, y0), x1 - x0, y1 - y0, color="0.82", zorder=0))
        ax.text((x0 + x1) / 2, (y0 + y1) / 2, m.split("/")[-1][:20], ha="center", fontsize=7)
    ax.set_xlim(die[0] - 5, die[2] + 5); ax.set_ylim(die[1] - 5, die[3] + 5); ax.set_aspect("equal"); ax.set_title(t, fontsize=9)
ax = axs[0][0]; base(ax, f"{title}: cells(grey) regs(blue) pin-regs(green) ports(black)\nFF hold viol launch->capture (orange), TT setup viol (purple)")
cx = [pos(i) for i in ins if i not in macros]
ax.hexbin([p[0] for p in cx], [p[1] for p in cx], gridsize=60, cmap="Greys", mincnt=1, alpha=.5)
regs = [i for i in ckpin if pos(i) and i not in macros]
ax.scatter([pos(i)[0] for i in regs if i not in pinreg], [pos(i)[1] for i in regs if i not in pinreg], s=.3, c="tab:blue")
g = [pos(i) for i in regs if i in pinreg]; 
if g: ax.scatter(*zip(*g), s=1, c="g")
if ports: ax.scatter(*zip(*ports.values()), s=1, c="k")
for r in H:
    if r["a"] and r["b"]: ax.annotate("", xy=r["b"], xytext=r["a"], arrowprops=dict(arrowstyle="->", color="orange", lw=.7))
for r in St:
    if r["a"] and r["b"]: ax.annotate("", xy=r["b"], xytext=r["a"], arrowprops=dict(arrowstyle="->", color="purple", lw=.7))
ax = axs[0][1]; base(ax, "clock tree (buffer->buffer/macro edges red, root star) + FF RCX arrival at sinks (ps, source latency 0)")
ks = [k for k in ck if pos(inst(k))]
sc = ax.scatter([pos(inst(k))[0] for k in ks], [pos(inst(k))[1] for k in ks], c=[ck[k] for k in ks], s=2, cmap="viridis"); plt.colorbar(sc, ax=ax, fraction=.04)
for d, sinks in cnets:
    if d.startswith("PORT:"):
        p = portpos(d[5:]); 
        if p: ax.plot(*p, "r*", ms=14)
        a = p
    else: a = pos(d)
    if not a: continue
    for s in sinks:
        si = s.rsplit("/", 1)[0]
        if si in drv or si in macros:
            b = pos(si); 
            if b: ax.plot([a[0], b[0]], [a[1], b[1]], c="r", lw=.35)
for m in macros:
    q = pos(m); a_ = arr(m, ck)
    if a_: ax.text(q[0], q[1] - 8, "clk FF %.0f" % a_, ha="center", fontsize=8, color="b")
ax = axs[0][2]; base(ax, "TT clock arrival GRT-estimate minus routed RCX (ps)")
if est:
    ks = [k for k in ckt if k in est and pos(inst(k))]
    sc = ax.scatter([pos(inst(k))[0] for k in ks], [pos(inst(k))[1] for k in ks], c=[est[k] - ckt[k] for k in ks], s=2, cmap="magma"); plt.colorbar(sc, ax=ax, fraction=.04)
ax = axs[1][0]; base(ax, "routing demand: global-route guide length per gcell (M2+), proxy for congestion")
if gd is not None:
    im = ax.imshow(gd, origin="lower", extent=(0, die[2], 0, die[3]), cmap="inferno", zorder=-1); plt.colorbar(im, ax=ax, fraction=.04)
ax = axs[1][1]; ax.set_title("pin->register Manhattan distance (um), in/out; macro IF reg distance to macro box", fontsize=9)
for d_, v in dist.items(): ax.hist(v, bins=40, alpha=.5, label=f"pin {d_} n={len(v)}")
for m, L in mif.items():
    r0 = ins[m]; x0, y0, x1, y1 = map(float, r0[3:7])
    ax.hist([max(x0 - pos(r)[0], 0, pos(r)[0] - x1) + max(y0 - pos(r)[1], 0, pos(r)[1] - y1) for _, _, r in L], bins=40, alpha=.5, histtype="step", lw=2, label=f"macro {m[:18]} IF n={len(L)}")
ax.legend(fontsize=7); ax.set_yscale("log")
ax = axs[1][2]; ax.axis("off")
txt = json.dumps({k: out[k] for k in out if k not in ("hold_ff", "setup_tt", "p2r_far")}, indent=0)[:1800]
txt += "\nHOLD " + json.dumps({k: v for k, v in out["hold_ff"].items() if k != "worst"})[:900]
txt += "\nSETUP " + json.dumps({k: v for k, v in out["setup_tt"].items() if k != "worst"})[:700]
ax.text(0, 1, txt, va="top", fontsize=6.5, family="monospace", wrap=True)
plt.tight_layout(); plt.savefig(f"{D}/review.png", dpi=80)
json.dump(out, open(f"{D}/review.json", "w"), indent=1, default=str)
print(json.dumps(out, indent=1, default=str)[:6000])
