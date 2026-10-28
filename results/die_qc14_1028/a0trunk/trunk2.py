#!/usr/bin/env python3
"""DIE-QC-14 A0 parent LOCAL trunk planner v2 (plan, not ECO). Successor of DIE-QC-12 trunk.py.
Changes vs trunk.py:
  * no padding-stage stacks: every merge balances by WIRE LENGTH (zero-skew DME elongation). The faster leg is
    lengthened along a detour ("bridge") polyline whose corners are repeater sites, so each CKINVDCx16 stage drives
    a real wire segment (<= sp um). Extra stages come only in parity pairs and only when the leg cannot take more wire.
  * child pins are balanced to the 12.3 common core latency contract (250 TT / 202.5 FF) instead of fixture ETM numbers.
  * romleaf leg ends at the a0k5 clk pin (21.612,15.12) and the parent db carries that pin (cl_nkr.odb, LEF round trip).
  * the tree is saved (merge nodes, legs, wire length) so corr mode can re-balance with MEASURED subtree arrivals:
    bottom-up, at each merge the slower leg is shortened (if it was elongated) and the faster leg lengthened by the
    measured mid-range difference; the model is used only for the small delay delta.
usage: trunk2.py plan <t> cl.json clins.json out.json [opts]
       trunk2.py corr <prev.json> arr_TT.txt out.json [opts]"""
import json, math, argparse, re, statistics as st
ap = argparse.ArgumentParser()
ap.add_argument("mode", choices=["plan", "corr"])
ap.add_argument("a1"); ap.add_argument("a2"); ap.add_argument("a3"); ap.add_argument("out", nargs="?")
ap.add_argument("--stage-table", default="stage_table.json")
ap.add_argument("--sp", type=float, default=110.0, help="max segment length um")
ap.add_argument("--sp-max", type=float, default=1.15, help="elongated segment may reach sp*this")
ap.add_argument("--entry", default="228.972,578.88")
ap.add_argument("--romleaf-pin", default="21.612,15.12")
ap.add_argument("--child-ins", default="ot_qwen_tile_lsl_rawfault_m3=250/202.5,ot_qwen_tile_node=250/202.5,"
                                       "ot_qwen_tile_romleaf=250/202.5")
ap.add_argument("--icg-ps", default="22,18")
ap.add_argument("--max-extra", type=int, default=12, help="extra stages (pairs) on an elongated leg")
ap.add_argument("--damp", type=float, default=1.0, help="corr: fraction of the measured imbalance corrected")
a = ap.parse_args()
TAB = json.load(open(a.stage_table))
CI = {k: tuple(map(float, v.split("/"))) for k, v in (x.split("=") for x in a.child_ins.split(","))}


def man(p, q):
    return abs(p[0] - q[0]) + abs(p[1] - q[1])


def _interp(C, fo, L):
    t = [(x[1], x[2]) for x in TAB[C] if x[0] == fo]
    if L <= t[0][0]:
        return t[0][1]
    for (l0, v0), (l1, v1) in zip(t, t[1:]):
        if L <= l1:
            return v0 + max(v1 - v0, 0.0) * (L - l0) / (l1 - l0)
    (l0, v0), (l1, v1) = t[-2], t[-1]
    sl = max((v1 - v0) / (l1 - l0), 0.40)
    return v1 + sl * (L - l1)


def seg(L, C="TT"):
    return _interp(C, 1, L)


def fo2(pts, C="TT"):
    L = man(pts[0], pts[1])
    return _interp(C, 2, L) - _interp(C, 1, L)


def legd(pts, C="TT"):
    return sum(seg(man(u, v), C) for u, v in zip(pts, pts[1:])) + fo2(pts, C)


# ---------------------------------------------------------------- geometry
G = None


def load_geom(cl):
    global G
    G = json.load(open(cl))


def inmac(x, y, h=1.0):
    return any(m[0] - h < x < m[2] + h and m[1] - h < y < m[3] + h for m in G["macros"])


def legal(p):
    W, H = G["W"], G["H"]
    x = min(max(p[0], 6.0), W - 6.0); y = min(max(p[1], 6.0), H - 6.0)
    if not inmac(x, y):
        return (round(x, 3), round(y, 3))
    best = None
    for m in G["macros"]:
        if m[0] - 1 < x < m[2] + 1 and m[1] - 1 < y < m[3] + 1:
            for c in ((m[0] - 1.5, y), (m[2] + 1.5, y), (x, m[1] - 1.5), (x, m[3] + 1.5)):
                if 6 <= c[0] <= W - 6 and 6 <= c[1] <= H - 6 and not inmac(*c):
                    dd = man(c, (x, y))
                    if best is None or dd < best[0]:
                        best = (dd, c)
    c = best[1] if best else (x, y)
    return (round(c[0], 3), round(c[1], 3))


def sample(poly, n):
    """n segments along a Manhattan polyline; every polyline corner is a repeater site when n allows."""
    secs = [(u, v, man(u, v)) for u, v in zip(poly, poly[1:]) if man(u, v) > 1e-6]
    if not secs:
        return [poly[0]] * (n + 1)
    tot = sum(s[2] for s in secs)
    if len(secs) > n:          # too few stages to sit on every corner: plain arc sampling
        secs = [(poly[0], poly[-1], tot)]
        flat = poly
        pts = [poly[0]]
        cum = [0.0]
        for u, v in zip(flat, flat[1:]):
            cum.append(cum[-1] + man(u, v))
        for j in range(1, n):
            s = tot * j / n
            k = max(i for i in range(len(cum) - 1) if cum[i] <= s)
            u, v = flat[k], flat[k + 1]; f = (s - cum[k]) / max(man(u, v), 1e-9)
            pts.append((u[0] + (v[0] - u[0]) * f, u[1] + (v[1] - u[1]) * f))
        pts.append(poly[-1])
        return pts
    k = [max(1, round(n * s[2] / tot)) for s in secs]
    while sum(k) > n:
        i = max(range(len(k)), key=lambda i: (k[i] > 1, k[i] / secs[i][2] if k[i] > 1 else -1)); k[i] -= 1
    while sum(k) < n:
        i = max(range(len(k)), key=lambda i: secs[i][2] / k[i]); k[i] += 1
    pts = [secs[0][0]]
    for (u, v, L), kk in zip(secs, k):
        for j in range(1, kk + 1):
            f = j / kk
            pts.append((u[0] + (v[0] - u[0]) * f, u[1] + (v[1] - u[1]) * f))
    return pts


def polys(q, p, Le):
    """candidate Manhattan polylines q->p of length ~Le: two L shapes (Le<=man) or four bridges (detour)."""
    L = man(q, p); out = []
    if Le <= L + 0.5:
        for hf in (True, False):
            c = (p[0], q[1]) if hf else (q[0], p[1])
            out.append([q, c, p])
        return out
    h = (Le - L) / 2.0
    ymax, ymin = max(q[1], p[1]), min(q[1], p[1]); xmax, xmin = max(q[0], p[0]), min(q[0], p[0])
    for wy in (ymax + h, ymin - h):
        out.append([q, (q[0], wy), (p[0], wy), p])
    for wx in (xmax + h, xmin - h):
        out.append([q, (wx, q[1]), (wx, p[1]), p])
    return out


def build_leg(q, p, n, Le, C="TT"):
    """best legal leg (pts incl. both ends) for n stages and target length Le; returns (delay, pts, wire)."""
    best = None
    for poly in polys(q, p, Le):
        raw = sample(poly, n)
        pts = [q] + [legal(x) for x in raw[1:-1]] + [p]
        segs = [man(u, v) for u, v in zip(pts, pts[1:])]
        wire = sum(segs)
        bad = sum(max(0.0, s - a.sp * a.sp_max) for s in segs)
        key = (bad > 1.0, abs(wire - Le) + 3 * bad)
        if best is None or key < best[0]:
            best = (key, pts, wire)
    pts = best[1]
    return legd(pts), pts, best[2]


def nmin(L, par):
    n = max(1, math.ceil(L / a.sp - 1e-9))
    return n + ((n - par) % 2)


def nd_tt(n, L):
    return n * seg(L / n)


def solve_len(n, L0, target):
    """wire length >= L0 for n stages whose model delay ~= target (None if > n*sp*sp_max)."""
    hi = n * a.sp * a.sp_max
    if nd_tt(n, hi) < target:
        return None
    lo = L0
    if nd_tt(n, lo) >= target:
        return lo
    for _ in range(40):
        m = (lo + hi) / 2
        if nd_tt(n, m) < target:
            lo = m
        else:
            hi = m
    return hi


def plan_merge(A, B):
    best = None
    D_ = man(A["p"], B["p"]); cands = set()
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
            for ea, eb in [(0, 0)] + [(e, 0) for e in range(2, a.max_extra + 1, 2)] + [(0, e) for e in range(2, a.max_extra + 1, 2)]:
                na, nb = nmin(La, (A["r"] - rM) % 2) + ea, nmin(Lb, (B["r"] - rM) % 2) + eb
                ta, tb = nd_tt(na, La) + A["tt"], nd_tt(nb, Lb) + B["tt"]
                Lea, Leb = La, Lb
                if ta < tb:
                    x = solve_len(na, La, tb - A["tt"]); Lea = x if x is not None else na * a.sp * a.sp_max
                    ta = nd_tt(na, Lea) + A["tt"]
                elif tb < ta:
                    x = solve_len(nb, Lb, ta - B["tt"]); Leb = x if x is not None else nb * a.sp * a.sp_max
                    tb = nd_tt(nb, Leb) + B["tt"]
                cost = abs(ta - tb) + 0.02 * (Lea + Leb - D_) + 4 * (ea + eb)
                if best is None or cost < best[0]:
                    best = (cost, q, rM, na, nb, Lea, Leb)
    _, q, rM, na, nb, Lea, Leb = best
    M = dict(kind="merge", p=list(q), r=rM, kids=[A, B],
             legs=[dict(n=na, Le=Lea), dict(n=nb, Le=Leb)])
    realize(M)
    refine(M)
    return M


def fit_leg(q, kid, lg, target, nmax_extra=6):
    """(n, Le, d) of a realisable leg (actual legalised geometry) whose model delay is closest to target;
    stages only in parity pairs, wire >= Manhattan."""
    base = man(q, tuple(kid["p"])); best = None
    n0 = nmin(base, (lg["n"]) % 2)
    for n in range(n0, n0 + nmax_extra + 1, 2):
        top_len = n * a.sp * a.sp_max
        for j in range(0, 61):
            Le = base + (top_len - base) * j / 60
            d, pts, w = build_leg(q, tuple(kid["p"]), n, Le)
            err = abs(d - target) + 2.0 * (n - n0) + 0.01 * (w - base)
            if best is None or err < best[0]:
                best = (err, n, Le, d)
    return best[1:]


def refine(M):
    """zero-skew on the realised geometry: re-fit the faster leg, else the slower one, to the other side."""
    if M["imb"] <= 2.0:
        return
    q = tuple(M["p"]); t = [lg["d_tt"] + k["tt"] for k, lg in zip(M["kids"], M["legs"])]
    f, s = (0, 1) if t[0] < t[1] else (1, 0)
    lg = M["legs"][f]; kid = M["kids"][f]
    n, Le, d = fit_leg(q, kid, lg, t[s] - kid["tt"])
    lg["n"], lg["Le"] = n, Le; realize(M)
    if M["imb"] > 2.0:   # slower leg carries elongation: shorten it
        t = [lg["d_tt"] + k["tt"] for k, lg in zip(M["kids"], M["legs"])]
        f, s = (0, 1) if t[0] < t[1] else (1, 0)
        lg = M["legs"][s]; kid = M["kids"][s]
        if lg["wire"] > man(q, tuple(kid["p"])) + 0.5:
            n, Le, d = fit_leg(q, kid, lg, t[f] - kid["tt"])
            lg["n"], lg["Le"] = n, Le; realize(M)


def realize(M):
    """(re)build both legs of a merge from n/Le and update the node's model arrivals."""
    q = tuple(M["p"]); tt, ff = [], []
    for kid, lg in zip(M["kids"], M["legs"]):
        d, pts, wire = build_leg(q, tuple(kid["p"]), lg["n"], lg["Le"])
        lg.update(pts=[list(x) for x in pts], wire=round(wire, 2), d_tt=round(d, 2), d_ff=round(legd(pts, "FF"), 2))
        tt.append(d + kid["tt"]); ff.append(lg["d_ff"] + kid["ff"])
    M["tt"], M["ff"] = max(tt), max(ff)
    M["imb"], M["imb_ff"] = round(abs(tt[0] - tt[1]), 1), round(abs(ff[0] - ff[1]), 1)


# ---------------------------------------------------------------- emit / summary
def emit_all(top, rootleg):
    insts = []; sinks = []

    def emit(nd, drv_net):
        if nd["kind"] != "merge":
            nd["net"] = drv_net; sinks.append(dict(kind=nd["kind"], name=nd["name"], net=drv_net, p=nd["p"]))
            return
        name = "a0t_m%d" % len(insts); nd["inst"] = name
        insts.append(dict(name=name, cell="CKINVDCx16_ASAP7_75t_R", p=list(nd["p"]), in_net=drv_net, out_net=name + "_o"))
        for kid, lg in zip(nd["kids"], nd["legs"]):
            net = name + "_o"
            for pt in lg["pts"][1:-1]:
                r = "a0t_r%d" % len(insts)
                insts.append(dict(name=r, cell="CKINVDCx16_ASAP7_75t_R", p=list(pt), in_net=net, out_net=r + "_o")); net = r + "_o"
            emit(kid, net)

    net = "a0t_gclk"
    for pt in rootleg[1:-1]:
        r = "a0t_r%d" % len(insts)
        insts.append(dict(name=r, cell="CKINVDCx16_ASAP7_75t_R", p=list(pt), in_net=net, out_net=r + "_o")); net = r + "_o"
    emit(top, net)
    return insts, sinks


def stats(top, rootleg, icg):
    arr = {}; wire = [man(u, v) for u, v in zip(rootleg, rootleg[1:])]; imbs = []; stacked = [0]

    def down(nd, t, tf, ninv):
        if nd["kind"] != "merge":
            arr[nd["name"]] = dict(tt=round(t + nd["tt"], 1), ff=round(tf + nd["ff"], 1), inv=ninv + (1 if nd["kind"] == "cluster" else 0))
            return
        imbs.append(nd["imb"])
        for kid, lg in zip(nd["kids"], nd["legs"]):
            wire.extend(man(u, v) for u, v in zip(lg["pts"], lg["pts"][1:]))
            stacked[0] += sum(1 for u, v in zip(lg["pts"][1:-1], lg["pts"][2:-1]) if man(u, v) < 8.0)
            down(kid, t + lg["d_tt"], tf + lg["d_ff"], ninv + len(lg["pts"]) - 1)

    itt, iff = map(float, a.icg_ps.split(","))
    down(top, itt + legd(rootleg), iff + legd(rootleg, "FF"), len(rootleg) - 2)
    v = [x["tt"] for x in arr.values()]; vf = [x["ff"] for x in arr.values()]
    elong = []

    def el(nd):
        if nd["kind"] == "merge":
            for kid, lg in zip(nd["kids"], nd["legs"]):
                elong.append(lg["wire"] - man(nd["p"], kid["p"])); el(kid)
    el(top)
    return arr, dict(plan_tt=dict(min=min(v), max=max(v), spread=round(max(v) - min(v), 1)),
                     plan_ff=dict(min=min(vf), max=max(vf), spread=round(max(vf) - min(vf), 1)),
                     merge_imb_max=max(imbs), trunk_wire_um=round(sum(wire), 1),
                     elongation_um=round(sum(x for x in elong if x > 0.5), 1), elongated_legs=sum(1 for x in elong if x > 0.5),
                     short_stage_pairs_lt8um=stacked[0],
                     odd_parity_sinks=[k for k, x in arr.items() if x["inv"] % 2])


def save(top, rootleg, icg, E, out, extra):
    insts, sinks = emit_all(top, rootleg)
    arr, sm = stats(top, rootleg, icg)
    summ = dict(entry=E, icg=dict(site=icg, cell="ICGx8DC_ASAP7_75t_R",
                note="QC-PG-4 per-tile ICG site at the A0 tile root; trial build ties ENA=1/SE=0 (RTL enable step separate)"),
                n_inv=len(insts), sinks=len(sinks), child_ins=CI, sp=a.sp, sp_max=a.sp_max, **sm, **extra)
    json.dump(dict(summary=summ, insts=insts, sinks=sinks, arrival_plan=arr, root_leg=[list(x) for x in rootleg],
                   tree=top, cl=G_path), open(out, "w"), indent=0)
    print(json.dumps(summ))


# ---------------------------------------------------------------- modes
if a.mode == "plan":
    t, cl, ins, out = a.a1, a.a2, a.a3, a.out
    G_path = cl; load_geom(cl); INS = json.load(open(ins)); macros = G["macros"]
    nodes = []
    for c in G["clusters"]:
        nodes.append(dict(kind="cluster", name=c["name"], p=list(c["root"]), tt=INS[c["name"]]["TT"]["mean"],
                          ff=INS[c["name"]]["FF"]["mean"], r=1))
    rp = tuple(map(float, a.romleaf_pin.split(",")))
    for k in G["kids"]:
        m = k["module"]; p = tuple(k["pin"])
        if m == "ot_qwen_tile_romleaf":
            mb = min(macros, key=lambda b: man(((b[0] + b[2]) / 2, (b[1] + b[3]) / 2), p))
            p = ((mb[2] - rp[0]) if mb[0] < 200 else (mb[0] + rp[0]), mb[1] + rp[1])   # col[0] MY, col[1] R0
        tt, ff = CI[m]
        nodes.append(dict(kind="child", name=k["inst"], module=m, p=[round(p[0], 3), round(p[1], 3)], tt=tt, ff=ff, r=0))
    live = list(nodes)
    k1 = 0.40
    while len(live) > 1:
        best = None
        for i in range(len(live)):
            for j in range(i + 1, len(live)):
                A, B = live[i], live[j]
                c = man(A["p"], B["p"]) + abs(A["tt"] - B["tt"]) / k1
                if best is None or c < best[0]:
                    best = (c, i, j)
        _, i, j = best
        M = plan_merge(live[i], live[j])
        live = [x for k, x in enumerate(live) if k not in (i, j)] + [M]
    top = live[0]
    E = tuple(map(float, a.entry.split(",")))
    icg = legal((E[0] + 3.0, E[1]))
    L = man(icg, top["p"]); n = max(1, math.ceil(L / a.sp))
    if (n - 1 - top["r"]) % 2:
        n += 1
    _, rootleg, _ = build_leg(icg, tuple(top["p"]), n, L)
    save(top, rootleg, list(icg), E, out, dict(iteration=0))
else:
    prev, arrf, out = a.a1, a.a2, a.a3
    P = json.load(open(prev)); G_path = P["cl"]; load_geom(G_path); top = P["tree"]
    CI = {k: tuple(v) for k, v in P["summary"]["child_ins"].items()}
    regs_by_net = {}; kidpin = {}; T = {}
    for l in open(arrf):
        p = l.split()
        if p[0] == "S":
            if p[2].startswith("ICG"):
                continue
            if p[2].startswith("ot_qwen"):
                kidpin[p[1][:-4].replace("\\", "")] = (p[2], float(p[4]))
            else:
                regs_by_net.setdefault(p[3], []).append(float(p[4]))
        else:
            T[p[1]] = float(p[2])
    clmeas = {}
    for s in P["sinks"]:
        if s["kind"] == "cluster":
            ms = [x for n, v in regs_by_net.items() if re.search(s["name"] + "$", n) for x in v]
            clmeas[s["name"]] = (min(ms), max(ms), st.mean(ms))
    moved = [0, 0.0, 0]

    def corr(nd):
        """returns (lo, hi) measured absolute sink arrival range under nd, after correcting its subtree."""
        if nd["kind"] == "cluster":
            lo, hi, mu = clmeas[nd["name"]]
            return [lo, hi]
        if nd["kind"] == "child":
            m, pa = kidpin[nd["name"].replace("\\", "")]
            v = pa + CI[m][0]
            return [v, v]
        rs = [corr(k) for k in nd["kids"]]
        mid = [(r[0] + r[1]) / 2 for r in rs]
        f, s = (0, 1) if mid[0] < mid[1] else (1, 0)
        need = (mid[s] - mid[f]) * a.damp
        if need > 1.0:
            q = tuple(nd["p"])
            # 1) shorten the slow leg if it carries elongation
            lgS = nd["legs"][s]; kS = nd["kids"][s]; base = man(q, tuple(kS["p"]))
            if lgS["wire"] > base + 0.5:
                d0 = lgS["d_tt"]; best = None
                for Le in [base + (lgS["wire"] - base) * j / 40 for j in range(41)]:
                    d, pts, w = build_leg(q, tuple(kS["p"]), lgS["n"], Le)
                    gain = d0 - d
                    if best is None or abs(min(gain, need) - need) + max(0, gain - need) < best[0]:
                        best = (abs(min(gain, need) - need) + max(0, gain - need), Le, gain)
                _, Le, gain = best
                if gain > 0.5:
                    lgS["Le"] = Le; realize(nd); rs[s] = [rs[s][0] - gain, rs[s][1] - gain]; need -= gain; moved[0] += 1
            # 2) lengthen the fast leg (more stages only in parity pairs, spread on the longer wire)
            if need > 1.0:
                lgF = nd["legs"][f]; kF = nd["kids"][f]; d0 = lgF["d_tt"]; best = None
                for n in (lgF["n"], lgF["n"] + 2, lgF["n"] + 4):
                    base = man(q, tuple(kF["p"]))
                    top_len = n * a.sp * a.sp_max
                    for j in range(0, 81):
                        Le = max(lgF["wire"] if n == lgF["n"] else base, base) + (top_len - base) * j / 80
                        if Le < base:
                            continue
                        d, pts, w = build_leg(q, tuple(kF["p"]), n, Le)
                        err = abs(d - d0 - need) + 3 * (n - lgF["n"])
                        if best is None or err < best[0]:
                            best = (err, n, Le, d - d0)
                _, n, Le, gain = best
                lgF["n"], lgF["Le"] = n, Le; realize(nd); rs[f] = [rs[f][0] + gain, rs[f][1] + gain]
                moved[1] += gain; moved[2] += 1
        return [min(r[0] for r in rs), max(r[1] for r in rs)]

    rng = corr(top)
    it = P["summary"].get("iteration", 0) + 1
    meas_before = dict(lo=round(rng[0], 1), hi=round(rng[1], 1))
    save(top, P["root_leg"], P["summary"]["icg"]["site"], P["summary"]["entry"], out,
         dict(iteration=it, corr_from=prev, legs_shortened=moved[0], legs_lengthened=moved[2],
              added_delay_ps=round(moved[1], 1), predicted_after=meas_before))
