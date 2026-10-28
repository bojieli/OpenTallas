#!/usr/bin/env python3
"""DIE-QC-12 A0 parent LOCAL trunk planner (plan, not ECO).
Centre entry ck -> ICG (QC-PG-4 per-tile ICG site at the A0 tile root, below the die crossing nodes) -> DME inverter
trunk (CKINVDCx16, every stage an inverter; parity by construction: even inversions port -> every flop) -> sinks:
  * glue-register cluster roots (CKINVDCx16 at the cluster site, TritonCTS local tree; insertion measured from root A)
  * child clock pins (insertion = the child view budget; romleaf leg aimed at the NEW romleaf clock pin (21.612,15.12))
Delay model per inverter stage driving a segment of L um into one CKINVDCx16: d = d0 + k1 L + k2 L^2 (TT; FF = x ffr).
usage: trunk.py <t> cl_<t>.json clins_<t>.json out.json [--model d0,k1,k2,ffr]"""
import json, math, argparse
ap = argparse.ArgumentParser()
ap.add_argument("t"); ap.add_argument("cl"); ap.add_argument("ins"); ap.add_argument("out")
ap.add_argument("--model", default="10,0.23,0.00121,0.82")
ap.add_argument("--model-ff", default=None, help="d0,k1,k2 FF stage model (fitted); default = TT x ffr")
ap.add_argument("--fo2", default="0,0", help="TT,FF ps added to each leg of a fanout-2 merge driver (fitted)")
ap.add_argument("--stage-table", default=None, help="empirical stage table (fit2.py) from built trunks")
ap.add_argument("--max-extra", type=int, default=8)
ap.add_argument("--sp", type=float, default=90.0, help="max segment length um")
ap.add_argument("--entry", default="228.972,578.88")
ap.add_argument("--romleaf-pin", default="21.612,15.12")
ap.add_argument("--child-ins", default="ot_qwen_tile_lsl_rawfault_m3=157.98/126.28,ot_qwen_tile_node=222.31/178.41,"
                                       "ot_qwen_tile_romleaf=170.29/139.94")
ap.add_argument("--icg-ps", default="22,18", help="ICG CLK->GCLK TT,FF model ps")
ap.add_argument("--topo", default="greedy", choices=["greedy", "mmm"])
ap.add_argument("--sink-adj", default=None, help="json {sink: [dtt, dff]} measured-model residual per sink (plan iteration)")
a = ap.parse_args()
d0, k1, k2, FFR = map(float, a.model.split(","))
D = json.load(open(a.cl)); INS = json.load(open(a.ins))
ADJ = json.load(open(a.sink_adj)) if a.sink_adj else {}
macros = D["macros"]; W, H = D["W"], D["H"]
CI = {k: tuple(map(float, v.split("/"))) for k, v in (x.split("=") for x in a.child_ins.split(","))}


def man(p, q):
    return abs(p[0] - q[0]) + abs(p[1] - q[1])


def inmac(x, y, h=1.0):
    return any(m[0] - h < x < m[2] + h and m[1] - h < y < m[3] + h for m in macros)


def legal(p):
    x = min(max(p[0], 6.0), W - 6.0); y = min(max(p[1], 6.0), H - 6.0)
    if not inmac(x, y):
        return (round(x, 3), round(y, 3))
    best = None
    for m in macros:
        if m[0] - 1 < x < m[2] + 1 and m[1] - 1 < y < m[3] + 1:
            for c in ((m[0] - 1.5, y), (m[2] + 1.5, y), (x, m[1] - 1.5), (x, m[3] + 1.5)):
                if 6 <= c[0] <= W - 6 and 6 <= c[1] <= H - 6 and not inmac(*c):
                    dd = man(c, (x, y))
                    if best is None or dd < best[0]:
                        best = (dd, c)
    c = best[1] if best else (x, y)
    return (round(c[0], 3), round(c[1], 3))


FO2T, FO2F = map(float, a.fo2.split(","))
MF = tuple(map(float, a.model_ff.split(","))) if a.model_ff else None


TAB = json.load(open(a.stage_table)) if a.stage_table else None


def _interp(C, fo, L):
    t = [(x[1], x[2]) for x in TAB[C] if x[0] == fo]
    if L <= t[0][0]:
        return t[0][1]
    for (l0, v0), (l1, v1) in zip(t, t[1:]):
        if L <= l1:
            return v0 + (v1 - v0) * (L - l0) / (l1 - l0)
    (l0, v0), (l1, v1) = t[-2], t[-1]
    sl = max((v1 - v0) / (l1 - l0), 0.40)
    return v1 + sl * (L - l1)


def seg(L):
    return _interp("TT", 1, L) if TAB else d0 + k1 * L + k2 * L * L


def segf(L):
    if TAB:
        return _interp("FF", 1, L)
    return (MF[0] + MF[1] * L + MF[2] * L * L) if MF else FFR * seg(L)


def fo2t(pts):
    return (_interp("TT", 2, man(pts[0], pts[1])) - _interp("TT", 1, man(pts[0], pts[1]))) if TAB else FO2T


def fo2f(pts):
    return (_interp("FF", 2, man(pts[0], pts[1])) - _interp("FF", 1, man(pts[0], pts[1]))) if TAB else FO2F


def legf(pts):
    return sum(segf(man(u, v)) for u, v in zip(pts, pts[1:]))


nodes = []
for c in D["clusters"]:
    ins = INS[c["name"]]; adj = ADJ.get(c["name"], [0, 0])
    nodes.append(dict(kind="cluster", name=c["name"], p=tuple(c["root"]), tt=ins["TT"]["mean"] + adj[0],
                      ff=ins["FF"]["mean"] + adj[1], r=1))
rp = tuple(map(float, a.romleaf_pin.split(",")))
for k in D["kids"]:
    m = k["module"]; p = tuple(k["pin"]); tgt = p
    if m == "ot_qwen_tile_romleaf":
        mb = min(macros, key=lambda b: man(((b[0] + b[2]) / 2, (b[1] + b[3]) / 2), p))
        # fixture orients: col[0] (x < 200) MY -> x mirrored; col[1] R0
        tgt = ((mb[2] - rp[0]) if mb[0] < 200 else (mb[0] + rp[0]), mb[1] + rp[1])
    tt, ff = CI[m]; adj = ADJ.get(k["inst"], [0, 0])
    nodes.append(dict(kind="child", name=k["inst"], module=m, p=tgt, pin_fixture=p, tt=tt + adj[0], ff=ff + adj[1], r=0))


def path_pts(q, p, n, hf):
    c = (p[0], q[1]) if hf else (q[0], p[1])
    L1, L = man(q, c), man(q, p)
    pts = [q]
    for j in range(1, n):
        s = L * j / n
        if s <= L1:
            pt = (q[0] + math.copysign(s, c[0] - q[0]), q[1]) if hf else (q[0], q[1] + math.copysign(s, c[1] - q[1]))
        else:
            pt = (c[0], c[1] + math.copysign(s - L1, p[1] - c[1])) if hf else (c[0] + math.copysign(s - L1, p[0] - c[0]), c[1])
        pts.append(legal(pt))
    pts.append(p)
    return pts


def leg(q, p, n):
    best = None
    for hf in (True, False):
        pts = path_pts(q, p, n, hf)
        dl = sum(seg(man(u, v)) for u, v in zip(pts, pts[1:]))
        mx = max(man(u, v) for u, v in zip(pts, pts[1:]))
        key = (mx > a.sp * 1.6, dl)
        if best is None or key < best[0]:
            best = (key, dl, pts)
    return best[1], best[2]


def nmin(L, par):
    n = max(1, math.ceil(L / a.sp - 1e-9))
    return n + ((n - par) % 2)


def merge(A, B):
    best = None
    D_ = man(A["p"], B["p"])
    cands = set()
    for hf in (True, False):
        c = (B["p"][0], A["p"][1]) if hf else (A["p"][0], B["p"][1])
        L1 = man(A["p"], c); steps = max(1, int(D_ / 3))
        for j in range(steps + 1):
            s = D_ * j / steps
            if s <= L1:
                pt = (A["p"][0] + math.copysign(s, c[0] - A["p"][0]), A["p"][1]) if hf else \
                     (A["p"][0], A["p"][1] + math.copysign(s, c[1] - A["p"][1]))
            else:
                pt = (c[0], c[1] + math.copysign(s - L1, B["p"][1] - c[1])) if hf else \
                     (c[0] + math.copysign(s - L1, B["p"][0] - c[0]), c[1])
            cands.add(legal(pt))
    for q in cands:
        La, Lb = man(q, A["p"]), man(q, B["p"])
        for rM in (0, 1):
            na0, nb0 = nmin(La, (A["r"] - rM) % 2), nmin(Lb, (B["r"] - rM) % 2)
            for ea in range(0, a.max_extra + 1, 2):
                for eb in range(0, a.max_extra + 1, 2):
                    if ea and eb:
                        continue
                    na, nb = na0 + ea, nb0 + eb
                    ta = na * seg(La / na) + A["tt"]; tb = nb * seg(Lb / nb) + B["tt"]
                    cost = abs(ta - tb) + 0.02 * (La + Lb - D_) + 2 * (ea + eb)
                    if best is None or cost < best[0]:
                        best = (cost, q, rM, na, nb)
    _, q, rM, na, nb = best
    da, pa = leg(q, A["p"], na); db, pb = leg(q, B["p"], nb)
    da += fo2t(pa); db += fo2t(pb)
    ta, tb = da + A["tt"], db + B["tt"]
    fa, fb = legf(pa) + fo2f(pa) + A["ff"], legf(pb) + fo2f(pb) + B["ff"]
    return dict(kind="merge", p=q, r=rM, tt=max(ta, tb), ff=max(fa, fb), imb=round(abs(ta - tb), 1),
                imb_ff=round(abs(fa - fb), 1), kids=[A, B], legs=[pa, pb])


ap2 = None
def mmm(items):
    """method of means and medians: recursive bisection of the sinks along the longer extent, merged bottom-up"""
    if len(items) == 1:
        return items[0]
    xs = [n["p"][0] for n in items]; ys = [n["p"][1] for n in items]
    ax = 0 if max(xs) - min(xs) >= max(ys) - min(ys) else 1
    items = sorted(items, key=lambda n: n["p"][ax]); h = len(items) // 2
    return merge(mmm(items[:h]), mmm(items[h:]))
live = list(nodes)
if a.topo == "mmm":
    live = [mmm(live)]
while len(live) > 1:     # greedy matching: least distance-plus-delay mismatch pair first (Edahiro-style)
    best = None
    for i in range(len(live)):
        for j in range(i + 1, len(live)):
            A, B = live[i], live[j]
            c = man(A["p"], B["p"]) + abs(A["tt"] - B["tt"]) / (k1 + d0 / a.sp)
            if best is None or c < best[0]:
                best = (c, i, j)
    _, i, j = best
    M = merge(live[i], live[j])
    live = [x for k, x in enumerate(live) if k not in (i, j)] + [M]
top = live[0]
E = tuple(map(float, a.entry.split(",")))
icg = legal((E[0] + 3.0, E[1]))
itt, iff = map(float, a.icg_ps.split(","))
L = man(icg, top["p"]); n = max(1, math.ceil(L / a.sp))
if (n - 1 - top["r"]) % 2:
    n += 1
dr, pr = leg(icg, top["p"], n)
insts = []


def emit(nd, drv_net):
    if nd["kind"] != "merge":
        nd["net"] = drv_net
        return
    name = "a0t_m%d" % len(insts)
    insts.append(dict(name=name, cell="CKINVDCx16_ASAP7_75t_R", p=list(nd["p"]), in_net=drv_net, out_net=name + "_o"))
    for kid, pts in zip(nd["kids"], nd["legs"]):
        net = name + "_o"
        for pt in pts[1:-1]:
            r = "a0t_r%d" % len(insts)
            insts.append(dict(name=r, cell="CKINVDCx16_ASAP7_75t_R", p=list(pt), in_net=net, out_net=r + "_o")); net = r + "_o"
        emit(kid, net)


net = "a0t_gclk"
for pt in pr[1:-1]:
    r = "a0t_r%d" % len(insts)
    insts.append(dict(name=r, cell="CKINVDCx16_ASAP7_75t_R", p=list(pt), in_net=net, out_net=r + "_o")); net = r + "_o"
emit(top, net)
imbs, wire = [], [man(u, v) for u, v in zip(pr, pr[1:])]


def walk(nd):
    if nd["kind"] == "merge":
        imbs.append(nd["imb"])
        for pts in nd["legs"]:
            wire.extend(man(u, v) for u, v in zip(pts, pts[1:]))
        for k in nd["kids"]:
            walk(k)


walk(top)
arr = {}


def down(nd, t, tf, ninv):
    if nd["kind"] != "merge":
        arr[nd["name"]] = dict(tt=round(t + nd["tt"], 1), ff=round(tf + nd["ff"], 1), inv=ninv + (1 if nd["kind"] == "cluster" else 0))
        return
    for kid, pts in zip(nd["kids"], nd["legs"]):
        dl = sum(seg(man(u, v)) for u, v in zip(pts, pts[1:])) + fo2t(pts)
        down(kid, t + dl, tf + legf(pts) + fo2f(pts), ninv + len(pts) - 1)


down(top, itt + dr, iff + legf(pr), len(pr) - 2)
v = [x["tt"] for x in arr.values()]; vf = [x["ff"] for x in arr.values()]
odd = [k for k, x in arr.items() if x["inv"] % 2]
summ = dict(entry=E, icg=dict(site=icg, cell="ICGx8DC_ASAP7_75t_R",
                              note="QC-PG-4 per-tile ICG site at the A0 tile root (below the die crossing nodes); enable from an "
                                   "existing signal with 1-cycle lead = RTL step; trial build ties ENA=1/SE=0"),
            n_inv=len(insts), sinks=len(nodes), model=dict(d0=d0, k1=k1, k2=k2, ffr=FFR, sp=a.sp),
            plan_tt=dict(min=min(v), max=max(v), spread=round(max(v) - min(v), 1)),
            plan_ff=dict(min=min(vf), max=max(vf), spread=round(max(vf) - min(vf), 1)),
            merge_imb_max=max(imbs), trunk_wire_um=round(sum(wire), 1), odd_parity_sinks=odd)
json.dump(dict(summary=summ, insts=insts, sinks=[dict(kind=nd["kind"], name=nd["name"], net=nd["net"], p=list(nd["p"]))
                                                 for nd in nodes], arrival_plan=arr, root_leg=[list(x) for x in pr]),
          open(a.out, "w"), indent=0)
print(json.dumps(summ))
