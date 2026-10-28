#!/usr/bin/env python3
"""Parent-tile LOCAL clock trunk planner, wire-length DME (opt-in shared tool; DIE-QC-15 upstream of DIE-QC-14 trunk2.py).

A parent tile (e.g. QC A0 nk) holds hard child macros (clock pin each, balanced to the 12.3 common core latency contract
250 TT / 202.5 FF) and glue registers grouped in local CTS clusters (one root inverter each).  This tool plans ONE tile
trunk from the tile entry (ICG site next to it) to every cluster root and child clock pin:

  * greedy zero-skew DME merges of CKINVDCx16 stages; even inversion parity to every sink by construction;
  * no padding-stage stacks: each merge balances by WIRE LENGTH (the faster leg is lengthened along a detour "bridge"
    polyline whose corners are repeater sites; stages are added only in parity pairs along the longer wire);
  * leg delays from a MEASURED per-stage table (stage delay vs segment length, fanout 1/2, per corner); every leg is
    realised on legalised geometry (no repeater inside a macro) before its delay is taken;
  * `corr` = measured re-balance on the SAME topology (plan iteration, not an ECO): bottom-up, the slower leg is
    shortened if it was elongated, else the faster one lengthened, by the measured mid-range difference.

Nothing in the shared flow calls this tool; it is OPT-IN (a kit calls it explicitly).  Default behaviour of every other
tool is unchanged.  Output json is byte-identical to the DIE-QC-14 lane planner (results/die_qc14_1028/a0trunk/trunk2.py)
for the same inputs and options (test_parent_trunk_dme.py).

usage:
  parent_trunk_dme.py plan GEOM.json CLUSTER_INS.json OUT.json --entry X,Y [--pin-offset MODULE=DX,DY ...] [opts]
  parent_trunk_dme.py corr PREV.json ARRIVALS_TT.txt OUT.json [opts]
  parent_trunk_dme.py tcl PLAN.json OUT.tcl          (ICG/TI/TS lists for parent_trunk_insert.tcl)

GEOM.json: {W, H, macros: [[x0,y0,x1,y1]...], clusters: [{name, root:[x,y], ...}], kids: [{inst, module, pin:[x,y]}]}
CLUSTER_INS.json: {cluster: {TT: {mean}, FF: {mean}}} (measured cluster-root -> register insertion)
ARRIVALS file lines: `S <pin> <ref> <net> <rise_max> ...` per clock pin (cluster nets end with the cluster name; child
pins are cells whose ref is a --child-ins module), as written by the meas step of the kit.
"""
import argparse
import json
import math
import re
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_TABLE = HERE / "parent_trunk_stage_table_ckinvdcx16.json"
DEFAULT_CHILD_INS = ("ot_qwen_tile_lsl_rawfault_m3=250/202.5,ot_qwen_tile_node=250/202.5,"
                     "ot_qwen_tile_romleaf=250/202.5")


def man(p, q):
    return abs(p[0] - q[0]) + abs(p[1] - q[1])


class Planner:
    def __init__(self, a, tab, geom):
        self.a = a
        self.TAB = tab
        self.G = geom

    # ------------------------------------------------------------ delay model (measured stage table)
    def _interp(self, C, fo, L):
        t = [(x[1], x[2]) for x in self.TAB[C] if x[0] == fo]
        if L <= t[0][0]:
            return t[0][1]
        for (l0, v0), (l1, v1) in zip(t, t[1:]):
            if L <= l1:
                return v0 + max(v1 - v0, 0.0) * (L - l0) / (l1 - l0)
        (l0, v0), (l1, v1) = t[-2], t[-1]
        sl = max((v1 - v0) / (l1 - l0), 0.40)
        return v1 + sl * (L - l1)

    def seg(self, L, C="TT"):
        return self._interp(C, 1, L)

    def fo2(self, pts, C="TT"):
        L = man(pts[0], pts[1])
        return self._interp(C, 2, L) - self._interp(C, 1, L)

    def legd(self, pts, C="TT"):
        return sum(self.seg(man(u, v), C) for u, v in zip(pts, pts[1:])) + self.fo2(pts, C)

    # ------------------------------------------------------------ geometry
    def inmac(self, x, y, h=1.0):
        return any(m[0] - h < x < m[2] + h and m[1] - h < y < m[3] + h for m in self.G["macros"])

    def legal(self, p):
        W, H = self.G["W"], self.G["H"]
        x = min(max(p[0], 6.0), W - 6.0); y = min(max(p[1], 6.0), H - 6.0)
        if not self.inmac(x, y):
            return (round(x, 3), round(y, 3))
        best = None
        for m in self.G["macros"]:
            if m[0] - 1 < x < m[2] + 1 and m[1] - 1 < y < m[3] + 1:
                for c in ((m[0] - 1.5, y), (m[2] + 1.5, y), (x, m[1] - 1.5), (x, m[3] + 1.5)):
                    if 6 <= c[0] <= W - 6 and 6 <= c[1] <= H - 6 and not self.inmac(*c):
                        dd = man(c, (x, y))
                        if best is None or dd < best[0]:
                            best = (dd, c)
        c = best[1] if best else (x, y)
        return (round(c[0], 3), round(c[1], 3))

    @staticmethod
    def sample(poly, n):
        """n segments along a Manhattan polyline; every polyline corner is a repeater site when n allows."""
        secs = [(u, v, man(u, v)) for u, v in zip(poly, poly[1:]) if man(u, v) > 1e-6]
        if not secs:
            return [poly[0]] * (n + 1)
        tot = sum(s[2] for s in secs)
        if len(secs) > n:          # too few stages to sit on every corner: plain arc sampling
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

    @staticmethod
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

    def build_leg(self, q, p, n, Le, C="TT"):
        """best legal leg (pts incl. both ends) for n stages and target length Le; returns (delay, pts, wire)."""
        a = self.a; best = None
        for poly in self.polys(q, p, Le):
            raw = self.sample(poly, n)
            pts = [q] + [self.legal(x) for x in raw[1:-1]] + [p]
            segs = [man(u, v) for u, v in zip(pts, pts[1:])]
            wire = sum(segs)
            bad = sum(max(0.0, s - a.sp * a.sp_max) for s in segs)
            key = (bad > 1.0, abs(wire - Le) + 3 * bad)
            if best is None or key < best[0]:
                best = (key, pts, wire)
        pts = best[1]
        return self.legd(pts), pts, best[2]

    def nmin(self, L, par):
        n = max(1, math.ceil(L / self.a.sp - 1e-9))
        return n + ((n - par) % 2)

    def nd_tt(self, n, L):
        return n * self.seg(L / n)

    def solve_len(self, n, L0, target):
        """wire length >= L0 for n stages whose model delay ~= target (None if > n*sp*sp_max)."""
        hi = n * self.a.sp * self.a.sp_max
        if self.nd_tt(n, hi) < target:
            return None
        lo = L0
        if self.nd_tt(n, lo) >= target:
            return lo
        for _ in range(40):
            m = (lo + hi) / 2
            if self.nd_tt(n, m) < target:
                lo = m
            else:
                hi = m
        return hi

    # ------------------------------------------------------------ DME merge
    def plan_merge(self, A, B):
        a = self.a; best = None
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
                cands.add(self.legal(pt))
        for q in cands:
            La, Lb = man(q, A["p"]), man(q, B["p"])
            for rM in (0, 1):
                for ea, eb in [(0, 0)] + [(e, 0) for e in range(2, a.max_extra + 1, 2)] + \
                              [(0, e) for e in range(2, a.max_extra + 1, 2)]:
                    na, nb = self.nmin(La, (A["r"] - rM) % 2) + ea, self.nmin(Lb, (B["r"] - rM) % 2) + eb
                    ta, tb = self.nd_tt(na, La) + A["tt"], self.nd_tt(nb, Lb) + B["tt"]
                    Lea, Leb = La, Lb
                    if ta < tb:
                        x = self.solve_len(na, La, tb - A["tt"]); Lea = x if x is not None else na * a.sp * a.sp_max
                        ta = self.nd_tt(na, Lea) + A["tt"]
                    elif tb < ta:
                        x = self.solve_len(nb, Lb, ta - B["tt"]); Leb = x if x is not None else nb * a.sp * a.sp_max
                        tb = self.nd_tt(nb, Leb) + B["tt"]
                    cost = abs(ta - tb) + 0.02 * (Lea + Leb - D_) + 4 * (ea + eb)
                    if best is None or cost < best[0]:
                        best = (cost, q, rM, na, nb, Lea, Leb)
        _, q, rM, na, nb, Lea, Leb = best
        M = dict(kind="merge", p=list(q), r=rM, kids=[A, B],
                 legs=[dict(n=na, Le=Lea), dict(n=nb, Le=Leb)])
        self.realize(M)
        self.refine(M)
        return M

    def fit_leg(self, q, kid, lg, target, nmax_extra=6):
        """(n, Le, d) of a realisable leg (actual legalised geometry) whose model delay is closest to target;
        stages only in parity pairs, wire >= Manhattan."""
        a = self.a; base = man(q, tuple(kid["p"])); best = None
        n0 = self.nmin(base, (lg["n"]) % 2)
        for n in range(n0, n0 + nmax_extra + 1, 2):
            top_len = n * a.sp * a.sp_max
            for j in range(0, 61):
                Le = base + (top_len - base) * j / 60
                d, pts, w = self.build_leg(q, tuple(kid["p"]), n, Le)
                err = abs(d - target) + 2.0 * (n - n0) + 0.01 * (w - base)
                if best is None or err < best[0]:
                    best = (err, n, Le, d)
        return best[1:]

    def refine(self, M):
        """zero-skew on the realised geometry: re-fit the faster leg, else the slower one, to the other side."""
        if M["imb"] <= 2.0:
            return
        q = tuple(M["p"]); t = [lg["d_tt"] + k["tt"] for k, lg in zip(M["kids"], M["legs"])]
        f, s = (0, 1) if t[0] < t[1] else (1, 0)
        lg = M["legs"][f]; kid = M["kids"][f]
        n, Le, d = self.fit_leg(q, kid, lg, t[s] - kid["tt"])
        lg["n"], lg["Le"] = n, Le; self.realize(M)
        if M["imb"] > 2.0:   # slower leg carries elongation: shorten it
            t = [lg["d_tt"] + k["tt"] for k, lg in zip(M["kids"], M["legs"])]
            f, s = (0, 1) if t[0] < t[1] else (1, 0)
            lg = M["legs"][s]; kid = M["kids"][s]
            if lg["wire"] > man(q, tuple(kid["p"])) + 0.5:
                n, Le, d = self.fit_leg(q, kid, lg, t[f] - kid["tt"])
                lg["n"], lg["Le"] = n, Le; self.realize(M)

    def realize(self, M):
        """(re)build both legs of a merge from n/Le and update the node's model arrivals."""
        q = tuple(M["p"]); tt, ff = [], []
        for kid, lg in zip(M["kids"], M["legs"]):
            d, pts, wire = self.build_leg(q, tuple(kid["p"]), lg["n"], lg["Le"])
            lg.update(pts=[list(x) for x in pts], wire=round(wire, 2), d_tt=round(d, 2),
                      d_ff=round(self.legd(pts, "FF"), 2))
            tt.append(d + kid["tt"]); ff.append(lg["d_ff"] + kid["ff"])
        M["tt"], M["ff"] = max(tt), max(ff)
        M["imb"], M["imb_ff"] = round(abs(tt[0] - tt[1]), 1), round(abs(ff[0] - ff[1]), 1)

    # ------------------------------------------------------------ emit / summary
    def emit_all(self, top, rootleg):
        a = self.a; insts = []; sinks = []
        cell = a.inv_cell; pre = a.prefix

        def emit(nd, drv_net):
            if nd["kind"] != "merge":
                nd["net"] = drv_net; sinks.append(dict(kind=nd["kind"], name=nd["name"], net=drv_net, p=nd["p"]))
                return
            name = "%s_m%d" % (pre, len(insts)); nd["inst"] = name
            insts.append(dict(name=name, cell=cell, p=list(nd["p"]), in_net=drv_net, out_net=name + "_o"))
            for kid, lg in zip(nd["kids"], nd["legs"]):
                net = name + "_o"
                for pt in lg["pts"][1:-1]:
                    r = "%s_r%d" % (pre, len(insts))
                    insts.append(dict(name=r, cell=cell, p=list(pt), in_net=net, out_net=r + "_o")); net = r + "_o"
                emit(kid, net)

        net = pre + "_gclk"
        for pt in rootleg[1:-1]:
            r = "%s_r%d" % (pre, len(insts))
            insts.append(dict(name=r, cell=cell, p=list(pt), in_net=net, out_net=r + "_o")); net = r + "_o"
        emit(top, net)
        return insts, sinks

    def stats(self, top, rootleg):
        arr = {}; wire = [man(u, v) for u, v in zip(rootleg, rootleg[1:])]; imbs = []; stacked = [0]

        def down(nd, t, tf, ninv):
            if nd["kind"] != "merge":
                arr[nd["name"]] = dict(tt=round(t + nd["tt"], 1), ff=round(tf + nd["ff"], 1),
                                       inv=ninv + (1 if nd["kind"] == "cluster" else 0))
                return
            imbs.append(nd["imb"])
            for kid, lg in zip(nd["kids"], nd["legs"]):
                wire.extend(man(u, v) for u, v in zip(lg["pts"], lg["pts"][1:]))
                stacked[0] += sum(1 for u, v in zip(lg["pts"][1:-1], lg["pts"][2:-1]) if man(u, v) < 8.0)
                down(kid, t + lg["d_tt"], tf + lg["d_ff"], ninv + len(lg["pts"]) - 1)

        itt, iff = map(float, self.a.icg_ps.split(","))
        down(top, itt + self.legd(rootleg), iff + self.legd(rootleg, "FF"), len(rootleg) - 2)
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
                         elongation_um=round(sum(x for x in elong if x > 0.5), 1),
                         elongated_legs=sum(1 for x in elong if x > 0.5),
                         short_stage_pairs_lt8um=stacked[0],
                         odd_parity_sinks=[k for k, x in arr.items() if x["inv"] % 2])

    def save(self, top, rootleg, icg, E, out, extra, CI, geom_path):
        a = self.a
        insts, sinks = self.emit_all(top, rootleg)
        arr, sm = self.stats(top, rootleg)
        summ = dict(entry=E, icg=dict(site=icg, cell=a.icg_cell, note=a.icg_note),
                    n_inv=len(insts), sinks=len(sinks), child_ins=CI, sp=a.sp, sp_max=a.sp_max, **sm, **extra)
        json.dump(dict(summary=summ, insts=insts, sinks=sinks, arrival_plan=arr, root_leg=[list(x) for x in rootleg],
                       tree=top, cl=geom_path), open(out, "w"), indent=0)
        print(json.dumps(summ))
        return summ


def parse_child_ins(s):
    return {k: tuple(map(float, v.split("/"))) for k, v in (x.split("=") for x in s.split(","))}


def kid_pin(k, macros, W, offsets, orient_rule):
    """child clock pin: the geometry pin, or (--pin-offset) the module's R0 pin offset in the nearest macro, mirrored
    in x for MY macros.  Orientation: the geometry kid's 'orient', else --orient-rule X (macro x0 < X -> MY, else R0);
    neither -> ValueError (fail closed, no silent guess).  QC A0 nk: col[0] MY, col[1] R0 -> --orient-rule 200."""
    m = k["module"]; p = tuple(k["pin"])
    if m not in offsets:
        return p
    rp = offsets[m]
    mb = min(macros, key=lambda b: man(((b[0] + b[2]) / 2, (b[1] + b[3]) / 2), p))
    orient = k.get("orient")
    if orient is None:
        if orient_rule is None:
            raise ValueError("pin offset for %s needs an orientation: geometry kid 'orient' (R0|MY) or --orient-rule"
                             % k["inst"])
        orient = "MY" if mb[0] < orient_rule else "R0"
    if orient not in ("R0", "MY"):
        raise ValueError("unsupported orient %r for %s (R0|MY)" % (orient, k["inst"]))
    return ((mb[2] - rp[0]) if orient == "MY" else (mb[0] + rp[0]), mb[1] + rp[1])


def check_geom(G, INS):
    for key in ("W", "H", "macros", "clusters", "kids"):
        if key not in G:
            raise ValueError("geometry json lacks %r" % key)
    miss = [c["name"] for c in G["clusters"] if c["name"] not in INS]
    if miss:
        raise ValueError("cluster insertion missing for %d clusters (e.g. %s)" % (len(miss), miss[0]))


def do_plan(a):
    TAB = json.load(open(a.stage_table)); G = json.load(open(a.a1)); INS = json.load(open(a.a2))
    check_geom(G, INS)
    CI = parse_child_ins(a.child_ins)
    unk = sorted({k["module"] for k in G["kids"]} - set(CI))
    if unk:
        raise ValueError("child module(s) without a --child-ins budget: %s" % unk)
    P = Planner(a, TAB, G); macros = G["macros"]
    offsets = {}
    for x in a.pin_offset or []:
        m, v = x.split("="); offsets[m] = tuple(map(float, v.split(",")))
    nodes = []
    for c in G["clusters"]:
        nodes.append(dict(kind="cluster", name=c["name"], p=list(c["root"]), tt=INS[c["name"]]["TT"]["mean"],
                          ff=INS[c["name"]]["FF"]["mean"], r=1))
    for k in G["kids"]:
        p = kid_pin(k, macros, G["W"], offsets, a.orient_rule)
        tt, ff = CI[k["module"]]
        nodes.append(dict(kind="child", name=k["inst"], module=k["module"], p=[round(p[0], 3), round(p[1], 3)],
                          tt=tt, ff=ff, r=0))
    if len(nodes) < 2:
        raise ValueError("need >= 2 sinks")
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
        M = P.plan_merge(live[i], live[j])
        live = [x for k, x in enumerate(live) if k not in (i, j)] + [M]
    top = live[0]
    E = tuple(map(float, a.entry.split(",")))
    ox, oy = map(float, a.icg_offset.split(","))
    icg = P.legal((E[0] + ox, E[1] + oy))
    L = man(icg, top["p"]); n = max(1, math.ceil(L / a.sp))
    if (n - 1 - top["r"]) % 2:
        n += 1
    _, rootleg, _ = P.build_leg(icg, tuple(top["p"]), n, L)
    return P.save(top, rootleg, list(icg), E, a.out, dict(iteration=0), CI, a.a1)


def read_arrivals(arrf, CI):
    regs_by_net = {}; kidpin = {}
    for l in open(arrf):
        p = l.split()
        if not p or p[0] != "S":
            continue
        if p[2].startswith("ICG"):
            continue
        if p[2] in CI:
            kidpin[p[1].rsplit("/", 1)[0].replace("\\", "")] = (p[2], float(p[4]))
        else:
            regs_by_net.setdefault(p[3], []).append(float(p[4]))
    return regs_by_net, kidpin


def do_corr(a):
    TAB = json.load(open(a.stage_table))
    Pv = json.load(open(a.a1)); G = json.load(open(Pv["cl"])); top = Pv["tree"]
    # the plan's segment limits are part of the plan: corr must not silently change them
    for k in ("sp", "sp_max"):
        if getattr(a, k) != Pv["summary"][k]:
            raise ValueError("corr --%s %s differs from the plan's %s" % (k.replace("_", "-"), getattr(a, k),
                                                                           Pv["summary"][k]))
    P = Planner(a, TAB, G)
    CI = {k: tuple(v) for k, v in Pv["summary"]["child_ins"].items()}
    regs_by_net, kidpin = read_arrivals(a.a2, CI)
    clmeas = {}
    for s in Pv["sinks"]:
        if s["kind"] == "cluster":
            ms = [x for n, v in regs_by_net.items() if re.search(s["name"] + "$", n) for x in v]
            if not ms:
                raise ValueError("no measured registers for cluster %s" % s["name"])
            clmeas[s["name"]] = (min(ms), max(ms), st.mean(ms))
        elif s["name"].replace("\\", "") not in kidpin:
            raise ValueError("no measured child pin for %s" % s["name"])
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
                    d, pts, w = P.build_leg(q, tuple(kS["p"]), lgS["n"], Le)
                    gain = d0 - d
                    if best is None or abs(min(gain, need) - need) + max(0, gain - need) < best[0]:
                        best = (abs(min(gain, need) - need) + max(0, gain - need), Le, gain)
                _, Le, gain = best
                if gain > 0.5:
                    lgS["Le"] = Le; P.realize(nd); rs[s] = [rs[s][0] - gain, rs[s][1] - gain]; need -= gain
                    moved[0] += 1
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
                        d, pts, w = P.build_leg(q, tuple(kF["p"]), n, Le)
                        err = abs(d - d0 - need) + 3 * (n - lgF["n"])
                        if best is None or err < best[0]:
                            best = (err, n, Le, d - d0)
                _, n, Le, gain = best
                lgF["n"], lgF["Le"] = n, Le; P.realize(nd); rs[f] = [rs[f][0] + gain, rs[f][1] + gain]
                moved[1] += gain; moved[2] += 1
        return [min(r[0] for r in rs), max(r[1] for r in rs)]

    rng = corr(top)
    it = Pv["summary"].get("iteration", 0) + 1
    meas_before = dict(lo=round(rng[0], 1), hi=round(rng[1], 1))
    return P.save(top, Pv["root_leg"], Pv["summary"]["icg"]["site"], Pv["summary"]["entry"], a.a3,
                  dict(iteration=it, corr_from=a.a1, legs_shortened=moved[0], legs_lengthened=moved[2],
                       added_delay_ps=round(moved[1], 1), predicted_after=meas_before), CI, Pv["cl"])


def do_tcl(plan, out):
    d = json.load(open(plan)); s = d["summary"]
    with open(out, "w") as f:
        f.write("set ICG [list %.3f %.3f]\nset TI {}\nset TS {}\n" % tuple(s["icg"]["site"]))
        for i in d["insts"]:
            f.write("lappend TI [list %s %s %.3f %.3f %s %s]\n" % (i["name"], i["cell"], i["p"][0], i["p"][1],
                                                                  i["in_net"], i["out_net"]))
        for k in d["sinks"]:
            f.write("lappend TS [list %s {%s} %s]\n" % (k["kind"], k["name"], k["net"]))


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("mode", choices=["plan", "corr", "tcl"])
    ap.add_argument("a1"); ap.add_argument("a2"); ap.add_argument("a3", nargs="?"); ap.add_argument("out", nargs="?")
    ap.add_argument("--stage-table", default=str(DEFAULT_TABLE), help="measured stage delay vs segment length")
    ap.add_argument("--sp", type=float, default=110.0, help="max segment length um")
    ap.add_argument("--sp-max", type=float, default=1.15, help="elongated segment may reach sp*this")
    ap.add_argument("--entry", default=None, help="tile clock entry x,y (required for plan)")
    ap.add_argument("--icg-offset", default="3,0", help="ICG site = legal(entry + offset)")
    ap.add_argument("--pin-offset", action="append", help="MODULE=dx,dy child clk pin offset in its macro (R0)")
    ap.add_argument("--orient-rule", type=float, default=None,
                    help="x: a --pin-offset macro whose x0 < x is MY, else R0 (when the geometry has no 'orient')")
    ap.add_argument("--child-ins", default=DEFAULT_CHILD_INS, help="MODULE=TT/FF child insertion budgets")
    ap.add_argument("--icg-ps", default="22,18")
    ap.add_argument("--icg-cell", default="ICGx8DC_ASAP7_75t_R")
    ap.add_argument("--icg-note", default="QC-PG-4 per-tile ICG site at the A0 tile root; trial build ties ENA=1/SE=0 "
                                          "(RTL enable step separate)")
    ap.add_argument("--inv-cell", default="CKINVDCx16_ASAP7_75t_R")
    ap.add_argument("--prefix", default="a0t", help="instance/net name prefix")
    ap.add_argument("--max-extra", type=int, default=12, help="extra stages (pairs) on an elongated leg")
    ap.add_argument("--damp", type=float, default=1.0, help="corr: fraction of the measured imbalance corrected")
    return ap


def main(argv=None):
    a = build_parser().parse_args(argv)
    if a.mode == "tcl":
        do_tcl(a.a1, a.a2)
        return 0
    if a.mode == "plan":
        if a.entry is None or a.a3 is None:
            raise SystemExit("plan needs GEOM CLUSTER_INS OUT and --entry")
        a.out = a.a3
        do_plan(a)
    else:
        if a.a3 is None:
            raise SystemExit("corr needs PREV ARRIVALS OUT")
        do_corr(a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
