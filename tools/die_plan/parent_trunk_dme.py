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
  parent_trunk_dme.py ocv PLAN.json ARRIVALS_TT.txt ARRIVALS_FF.txt [OUT.json]   (OCV-inclusive spread, measured)
  parent_trunk_dme.py eco BUILT.json NEW.json ECO.tcl NEW_BUILT.json   (rebuild only the changed legs)

OPT-IN (DIE-QC-17): `plan --topology bipart` = balanced top-down bipartition topology (several deterministic split
variants, the one with the smallest plan-model OCV-inclusive spread wins), embedded with the same wire-length merges.
The default `--topology greedy` is the DIE-QC-15 planner, byte-identical.
OPT-IN (DIE-QC-18): `eco` = incremental build of a corr step: only legs whose geometry changed are rebuilt on the
as-built db (parent_trunk_grt.tcl MODE=inc keeps every other clock route), so corr iterates on deterministic arrivals.

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
        self.pull = None          # (entry xy, ps/um) -- opt-in bipart merge-point pull; None = DIE-QC-15 behaviour

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
                    if self.pull is not None:      # bipart only: prefer the merge point nearest the tile entry
                        cost += self.pull[1] * man(q, self.pull[0])
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
            if nd["kind"] == "icg":      # opt-in --ungated-split: the ICG below the root merge (non-inverting)
                nd["in_net"] = drv_net; net = pre + "_gclk"
                for pt in nd["legs"][0]["pts"][1:-1]:
                    r = "%s_r%d" % (pre, len(insts))
                    insts.append(dict(name=r, cell=cell, p=list(pt), in_net=net, out_net=r + "_o")); net = r + "_o"
                emit(nd["kids"][0], net)
                return
            if nd["kind"] != "merge":
                nd["net"] = drv_net
                sinks.append(dict(kind=nd["kind"], name=nd["name"], net=drv_net, p=nd["p"],
                                  **({"ungated": True} if nd.get("ungated") else {})))
                return
            name = "%s_m%d" % (pre, len(insts)); nd["inst"] = name
            insts.append(dict(name=name, cell=cell, p=list(nd["p"]), in_net=drv_net, out_net=name + "_o"))
            for kid, lg in zip(nd["kids"], nd["legs"]):
                net = name + "_o"
                for pt in lg["pts"][1:-1]:
                    r = "%s_r%d" % (pre, len(insts))
                    insts.append(dict(name=r, cell=cell, p=list(pt), in_net=net, out_net=r + "_o")); net = r + "_o"
                emit(kid, net)

        net = pre + ("_ckin" if has_icg(top) else "_gclk")
        for pt in rootleg[1:-1]:
            r = "%s_r%d" % (pre, len(insts))
            insts.append(dict(name=r, cell=cell, p=list(pt), in_net=net, out_net=r + "_o")); net = r + "_o"
        emit(top, net)
        return insts, sinks

    def stats(self, top, rootleg):
        arr = {}; wire = [man(u, v) for u, v in zip(rootleg, rootleg[1:])]; imbs = []; stacked = [0]

        def down(nd, t, tf, ninv):
            if nd["kind"] == "icg":
                lg = nd["legs"][0]
                wire.extend(man(u, v) for u, v in zip(lg["pts"], lg["pts"][1:]))
                down(nd["kids"][0], t + lg["d_tt"], tf + lg["d_ff"], ninv + len(lg["pts"]) - 2)
                return
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
        if has_icg(top):         # --ungated-split: the ICG delay sits on the gated branch (in its leg), not at the root
            itt = iff = 0.0
        down(top, itt + self.legd(rootleg), iff + self.legd(rootleg, "FF"), len(rootleg) - 2)
        v = [x["tt"] for x in arr.values()]; vf = [x["ff"] for x in arr.values()]
        elong = []

        def el(nd):
            if nd["kind"] in ("merge", "icg"):
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
        ic = find_icg(top)
        if ic is not None:
            summ["ungated_split"] = dict(root_net=a.prefix + "_ckin", icg_in=ic["in_net"], gclk=a.prefix + "_gclk",
                                         icg_ps=ic["legs"][0]["icg_ps"],
                                         ungated_sinks=sorted(s_["name"] for s_ in sinks if s_.get("ungated")))
        json.dump(dict(summary=summ, insts=insts, sinks=sinks, arrival_plan=arr, root_leg=[list(x) for x in rootleg],
                       tree=top, cl=geom_path), open(out, "w"), indent=0)
        print(json.dumps(summ))
        return summ


def find_icg(nd):
    """the ICG node of an --ungated-split plan tree (None for every other plan)"""
    if nd.get("kind") == "icg":
        return nd
    for k in nd.get("kids", []) if nd.get("kind") == "merge" else []:
        r = find_icg(k)
        if r is not None:
            return r
    return None


def has_icg(nd):
    return find_icg(nd) is not None


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
    ung = [c["name"] for c in G["clusters"] if c.get("ungated")]
    if ung and not a.ungated_split:
        raise ValueError("geometry flags %d ungated clusters (e.g. %s): plan them with --ungated-split" % (len(ung), ung[0]))
    for c in G["clusters"]:
        nodes.append(dict(kind="cluster", name=c["name"], p=list(c["root"]), tt=INS[c["name"]]["TT"]["mean"],
                          ff=INS[c["name"]]["FF"]["mean"], r=1, **({"ungated": True} if c.get("ungated") else {})))
    for k in G["kids"]:
        p = kid_pin(k, macros, G["W"], offsets, a.orient_rule)
        tt, ff = CI[k["module"]]
        nodes.append(dict(kind="child", name=k["inst"], module=k["module"], p=[round(p[0], 3), round(p[1], 3)],
                          tt=tt, ff=ff, r=0))
    if len(nodes) < 2:
        raise ValueError("need >= 2 sinks")
    if a.ungated_split:
        return do_plan_split(a, P, nodes, CI)
    if a.topology == "bipart":
        return do_plan_bipart(a, P, nodes, CI)
    top = greedy_top(P, nodes)
    E = tuple(map(float, a.entry.split(",")))
    ox, oy = map(float, a.icg_offset.split(","))
    icg = P.legal((E[0] + ox, E[1] + oy))
    L = man(icg, top["p"]); n = max(1, math.ceil(L / a.sp))
    if (n - 1 - top["r"]) % 2:
        n += 1
    _, rootleg, _ = P.build_leg(icg, tuple(top["p"]), n, L)
    return P.save(top, rootleg, list(icg), E, a.out, dict(iteration=0), CI, a.a1)


def greedy_top(P, nodes):
    """DIE-QC-15 greedy bottom-up nearest-pair zero-skew merging (the default topology)."""
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
    return live[0]


# ---------------------------------------------------------------- opt-in ungated split (QC-A0-KITS-9)
# --ungated-split: the A0 tile root splits into an UNGATED face branch (input-face registers, enable state, reset
# landing: clusters flagged "ungated" in the geometry) and the GATED branch (every other cluster + every hard child)
# behind ONE ICG (QC-PG-4 structure, OWNER option c).  Both branches are planned with the same zero-skew merges; the
# ICG (non-inverting, --icg-ps) sits at the gated subtree's root (legal(gated root + --icg-offset)) and is a node of
# the tree, so the ROOT merge balances face vs gated latency by wire length like any other merge (no separate face
# tree, no pad stacks).  The root leg starts at the tile entry on the clock port net (<prefix>_ckin = CLK_NET in
# parent_trunk_insert.tcl).  Without the flag the planner is unchanged; a geometry with ungated clusters needs it.
def _sub_top(a, P, nodes):
    if len(nodes) == 1:
        return dict(nodes[0])
    if a.topology != "bipart":
        return greedy_top(P, nodes)
    T = _load_aocv(a.aocv_table); best = None
    for top_ in ("type", "geo"):
        for rule in ("delay", "count"):
            for ax in (None, 0, 1):
                t = bipart_topology(nodes, top_, rule, ax)
                tp = embed(P, t)
                arr, sm = P.stats(tp, [tp["p"], tp["p"]])
                rng = {C: {k.replace("\\", ""): (x[C.lower()], x[C.lower()]) for k, x in arr.items()} for C in ("TT", "FF")}
                oc = ocv_spread(T, tp, rng)
                k = (round(max(oc["TT"]["ocv_inclusive_spread"], oc["FF"]["ocv_inclusive_spread"]), 1),
                     sm["plan_tt"]["max"], "%s/%s/%s" % (top_, rule, ax))
                if best is None or k < best[0]:
                    best = (k, tp)
    return best[1]


def do_plan_split(a, P, nodes, CI):
    gated = [n for n in nodes if not n.get("ungated")]; ung = [n for n in nodes if n.get("ungated")]
    if not gated or not ung:
        raise ValueError("--ungated-split needs >= 1 ungated cluster and >= 1 gated sink (got %d / %d)"
                         % (len(ung), len(gated)))
    G = _sub_top(a, P, gated); U = _sub_top(a, P, ung)
    itt, iff = map(float, a.icg_ps.split(","))
    ox, oy = map(float, a.icg_offset.split(","))
    icg = P.legal((G["p"][0] + ox, G["p"][1] + oy))
    L = man(icg, G["p"]); n = max(1, math.ceil(L / a.sp))
    if (n - 1 - G["r"]) % 2:
        n += 1
    _, gpts, gw = P.build_leg(icg, tuple(G["p"]), n, L)
    leg = dict(n=n, Le=L, pts=[list(x) for x in gpts], wire=round(gw, 2), d_tt=round(itt + P.legd(gpts), 2),
               d_ff=round(iff + P.legd(gpts, "FF"), 2), icg_ps=[itt, iff])
    I = dict(kind="icg", name=a.prefix + "_icg", cell=a.icg_cell, p=list(icg), r=0,
             tt=leg["d_tt"] + G["tt"], ff=leg["d_ff"] + G["ff"], kids=[G], legs=[leg])
    top = P.plan_merge(I, U)
    E = tuple(map(float, a.entry.split(",")))
    L = man(E, top["p"]); n = max(1, math.ceil(L / a.sp))
    if (n - 1 - top["r"]) % 2:
        n += 1
    _, rootleg, _ = P.build_leg(E, tuple(top["p"]), n, L)
    arr, sm = P.stats(top, rootleg)
    T = _load_aocv(a.aocv_table)
    rng = {C: {k.replace("\\", ""): (x[C.lower()], x[C.lower()]) for k, x in arr.items()} for C in ("TT", "FF")}
    extra = dict(iteration=0, topology=a.topology, plan_ocv=ocv_spread(T, top, rng),
                 split_root=dict(gated_tt=round(I["tt"], 1), ungated_tt=round(U["tt"], 1), root_imb=top["imb"],
                                 root_imb_ff=top["imb_ff"], ungated_sinks=len(ung), gated_sinks=len(gated)))
    return P.save(top, rootleg, list(icg), list(E), a.out, extra, CI, a.a1)


# ---------------------------------------------------------------- opt-in balanced top-down bipartition (DIE-QC-17)
# --topology bipart: the topology comes from a recursive top-down bipartition of the sink set (instead of greedy
# bottom-up nearest-pair merging, which can leave a far singleton for the root merge: A0 nl a0cl1, 1051 of 2043 um
# elongation), then it is embedded bottom-up with the SAME zero-skew wire-length merge (plan_merge).  Several
# deterministic split variants are embedded and the one with the smallest OCV-INCLUSIVE spread (plan model, approved
# clock AOCV table, hold convention, CPPR at the pair's LCA) wins; ties -> lower insertion.  Default (greedy) unchanged.
EST_PS_PER_UM = 0.43     # CKINVDCx16 at ~110 um (stage table, TT) -- split heuristic only, never a reported number


def _bbox(pts):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def _est_lat(sub):
    """crude latency of a subtree over sinks `sub`: max(sink tt + ps/um * distance to the subset centroid)"""
    cx = sum(n["p"][0] for n in sub) / len(sub); cy = sum(n["p"][1] for n in sub) / len(sub)
    return max(n["tt"] + EST_PS_PER_UM * man(n["p"], (cx, cy)) for n in sub)


def _geo_split(sub, rule, axis=None):
    x0, y0, x1, y1 = _bbox([n["p"] for n in sub])
    ax = axis if axis is not None else (0 if (x1 - x0) >= (y1 - y0) else 1)
    order = sorted(sub, key=lambda n: (n["p"][ax], n["p"][1 - ax], n["name"]))
    m = len(order)
    if rule == "count" or m < 4:
        k = m // 2
    else:   # "delay": cut in the middle half that best balances the two subtree latencies (+ their extents)
        best = None
        for k in range(max(1, m // 4), min(m - 1, (3 * m + 3) // 4) + 1):
            A, B = order[:k], order[k:]
            ha = sum(b - a for a, b in zip(_bbox([n["p"] for n in A])[:2], _bbox([n["p"] for n in A])[2:]))
            hb = sum(b - a for a, b in zip(_bbox([n["p"] for n in B])[:2], _bbox([n["p"] for n in B])[2:]))
            c = abs(_est_lat(A) - _est_lat(B)) + EST_PS_PER_UM * 0.5 * (ha + hb)
            if best is None or c < best[0] - 1e-9:
                best = (c, k)
        k = best[1]
    return order[:k], order[k:]


def bipart_topology(sinks, top, rule, axis0):
    """nested binary topology (lists of sink dicts).  top='type': the root splits children from glue clusters (the
    children's 12.3 contract latency then sits on ONE shared elongated leg of the cluster side, not on every leaf
    merge); top='geo': geometric from the root.  axis0 forces the first geometric cut axis (None = longer side)."""
    def rec(sub, first):
        if len(sub) == 1:
            return sub[0]
        A, B = _geo_split(sub, rule, axis0 if first else None)
        return [rec(A, False), rec(B, False)]
    if top == "type":
        ch = [n for n in sinks if n["kind"] == "child"]; cl = [n for n in sinks if n["kind"] != "child"]
        if ch and cl:
            return [rec(ch, True), rec(cl, True)]
    return rec(sinks, True)


def embed(P, t, pull=None):
    """bottom-up zero-skew embedding of topology t; `pull` (entry, ps/um) biases only the ROOT merge point toward the
    tile entry (a shorter root leg; lower merges stay at their balance points)."""
    if isinstance(t, dict):
        return dict(t)
    A, B = embed(P, t[0]), embed(P, t[1])
    P.pull = pull
    try:
        return P.plan_merge(A, B)
    finally:
        P.pull = None


def _paths(top):
    paths = {}

    def walk(n, path):
        for lg, k in zip(n.get("legs", []), n.get("kids", [])):
            p2 = path + [lg]
            if k["kind"] in ("merge", "icg"):
                walk(k, p2)
            else:
                paths[k["name"].replace("\\", "")] = (p2, k)
    walk(top, [])
    return paths


def ocv_spread(T, top, rng, corners=("TT", "FF")):
    """OCV-inclusive spread = max over ordered sink pairs (capture b late, launch a early) of rng[b].hi - rng[a].lo +
    AOCV pessimism of the two branches below their LCA (planned legs: delay, stage count, bounding box; a cluster's
    local tree delay is added to its branch; a child's own insertion is its signed view's and is not charged here).
    Same region -> no droop term.  rng = {corner: {sink: (lo, hi)}}.  Same method as results/die_qc16_1028 nl_ocv.py."""
    import clk_aocv as AO
    paths = _paths(top); out = {}
    for C in corners:
        key = "d_tt" if C == "TT" else "d_ff"; sh = T["classes"]["A"][C]["cell_share"]
        R = rng[C]; names = sorted(n for n in R if n in paths)
        miss = sorted(n for n in R if n not in paths)
        if miss:
            raise ValueError("arrivals for sinks not in the plan tree: %s" % miss[:3])

        def branch(n, dpt):
            p, k = paths[n]; d = 0.0; stg = 0; xs = []
            for lg in p[dpt:]:
                d += lg[key]; stg += lg["n"]; xs += lg["pts"]
            if k["kind"] == "cluster":
                d += k[C.lower()]
            return dict(cell_ps=d * sh, net_ps=d * (1 - sh), stages={"A": max(stg, 1)}), xs
        worst = None
        for a_ in names:
            for b_ in names:
                if a_ == b_:
                    continue
                pa, pb = paths[a_][0], paths[b_][0]; dpt = 0
                while dpt < min(len(pa), len(pb)) and pa[dpt] is pb[dpt]:
                    dpt += 1
                ba, xa = branch(a_, dpt); bb, xb = branch(b_, dpt)
                xy = xa + xb + [paths[a_][1]["p"], paths[b_][1]["p"]]
                diag = (max(x for x, _ in xy) - min(x for x, _ in xy)) + (max(y for _, y in xy) - min(y for _, y in xy))
                pes = AO.branch_pessimism(T, C, ba, bb, diag, True, "hold")
                s = R[b_][1] - R[a_][0] + pes
                if worst is None or s > worst[0]:
                    worst = (s, [a_, b_, round(R[b_][1] - R[a_][0], 1), round(pes, 1)])
        nom = max(v[1] for v in R.values()) - min(v[0] for v in R.values())
        out[C] = dict(nominal_spread=round(nom, 1), ocv_inclusive_spread=round(worst[0], 1), worst_pair=worst[1],
                      sinks=len(names))
    return out


def _load_aocv(path):
    sys.path.insert(0, str(HERE))
    import clk_aocv as AO
    return AO.load(path)


def _root_leg(P, a, top):
    E = tuple(map(float, a.entry.split(",")))
    ox, oy = map(float, a.icg_offset.split(","))
    icg = P.legal((E[0] + ox, E[1] + oy))
    L = man(icg, top["p"]); n = max(1, math.ceil(L / a.sp))
    if (n - 1 - top["r"]) % 2:
        n += 1
    _, rootleg, _ = P.build_leg(icg, tuple(top["p"]), n, L)
    return E, icg, rootleg


def do_plan_bipart(a, P, nodes, CI):
    T = _load_aocv(a.aocv_table)
    variants = []
    for top in ("type", "geo"):
        for rule in ("delay", "count"):
            for ax in (None, 0, 1):
                variants.append((top, rule, ax))
    pulls = [float(x) for x in a.bipart_pull.split(",")]
    E0 = tuple(map(float, a.entry.split(",")))
    if a.bipart_variants:
        keep = set(a.bipart_variants.split(","))
        variants = [v for v in variants if "%s/%s/%s" % (v[0], v[1], "auto" if v[2] is None else "xy"[v[2]]) in keep]
        # (pull weights are chosen by --bipart-pull)
        if not variants:
            raise ValueError("--bipart-variants selects none of the variants")
    seen = {}; res = []
    for v, w in [(v, w) for v in variants for w in pulls]:
        t = bipart_topology(nodes, *v)
        sig = json.dumps(t, sort_keys=True, default=str) + "|%g" % w
        if sig in seen:                                    # same topology from another variant: embed once
            continue
        seen[sig] = v
        top = embed(P, t, (E0, w) if w > 0 else None)
        E, icg, rootleg = _root_leg(P, a, top)
        arr, sm = P.stats(top, rootleg)
        rng = {C: {k.replace("\\", ""): (x[C.lower()], x[C.lower()]) for k, x in arr.items()} for C in ("TT", "FF")}
        oc = ocv_spread(T, top, rng)
        obj = max(oc["TT"]["ocv_inclusive_spread"], oc["FF"]["ocv_inclusive_spread"])
        name = "%s/%s/%s/p%g" % (v[0], v[1], "auto" if v[2] is None else "xy"[v[2]], w)
        res.append(dict(variant=name, ocv_tt=oc["TT"]["ocv_inclusive_spread"], ocv_ff=oc["FF"]["ocv_inclusive_spread"],
                        insertion_tt=sm["plan_tt"]["max"], insertion_ff=sm["plan_ff"]["max"],
                        elongation_um=sm["elongation_um"], _k=(round(obj, 1), sm["plan_tt"]["max"], name),
                        _p=(top, E, icg, rootleg, oc)))
        print("bipart %-16s ocv TT/FF %6.1f %6.1f  insertion TT %6.1f  elong %7.1f" %
              (name, res[-1]["ocv_tt"], res[-1]["ocv_ff"], res[-1]["insertion_tt"], res[-1]["elongation_um"]),
              file=sys.stderr)
    best = min(res, key=lambda r: r["_k"])
    top, E, icg, rootleg, oc = best["_p"]
    table = [{k: v for k, v in r.items() if not k.startswith("_")} for r in res]
    extra = dict(iteration=0, topology="bipart", bipart_variant=best["variant"], bipart_objective="max(TT,FF) "
                 "OCV-inclusive spread, plan model (aocv %s)" % Path(a.aocv_table).name,
                 plan_ocv=oc, bipart_table=table)
    return P.save(top, rootleg, list(icg), E, a.out, extra, CI, a.a1)


def do_ocv(a):
    """OCV-inclusive spread of a plan on MEASURED arrivals (kit meas format, TT + FF): cluster = its registers' min..max,
    child = pin + its --child-ins contract (same convention as the plan)."""
    T = _load_aocv(a.aocv_table)
    Pv = json.load(open(a.a1)); G = json.load(open(Pv["cl"]))
    CI = {k: tuple(v) for k, v in Pv["summary"]["child_ins"].items()}
    reg2cl = {r.replace("\\", ""): c["name"] for c in G["clusters"] for r in c.get("regs", [])}
    rng = {}
    for C, ci, f in (("TT", 0, a.a2), ("FF", 1, a.a3)):
        R = {}
        for l in open(f):
            p = l.split()
            if not p or p[0] != "S" or p[2].startswith("ICG"):
                continue
            inst = p[1].rsplit("/", 1)[0].replace("\\", "")
            if p[2] in CI:
                nm = inst; v = float(p[4]) + CI[p[2]][ci]
            else:
                nm = reg2cl.get(inst); v = float(p[4])
                if nm is None:
                    continue
            lo, hi = R.get(nm, (1e18, -1e18)); R[nm] = (min(lo, v), max(hi, v))
        want = {s["name"].replace("\\", "") for s in Pv["sinks"]}
        if set(R) != want:
            raise ValueError("%s arrivals miss %d plan sinks (e.g. %s)" % (C, len(want - set(R)), sorted(want - set(R))[:2]))
        rng[C] = R
    oc = ocv_spread(T, Pv["tree"], rng)
    print(json.dumps(oc))
    if a.out:
        json.dump(oc, open(a.out, "w"), indent=1)
    return oc


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
        if nd["kind"] == "icg":          # --ungated-split: no balancing at the ICG; its parent merge balances it
            return corr(nd["kids"][0])
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


# ------------------------------------------------------------ opt-in incremental build (DIE-QC-18)
def _legs(d, prefix):
    """the plan's legs in emit order: (key, pts, repeater inst dicts, source net, kid node); kid input nets resolved.
    Works on a fresh plan (sequential names) and on an as-built plan written by `eco` (insts kept in emit order)."""
    it = iter(d["insts"]); legs = []; byname = {}

    def take(n):
        out = []
        for _ in range(n):
            x = next(it, None)
            if x is None:
                raise ValueError("plan insts shorter than its tree")
            out.append(x)
        return out

    rl = d["root_leg"]; rr = take(len(rl) - 2)
    root = dict(key="R", pts=rl, reps=rr, src=None, kid=d["tree"]); legs.append(root)

    def node(nd, key):
        if nd["kind"] != "merge":
            return
        m = take(1)[0]
        if m["name"] != nd.get("inst"):
            raise ValueError("plan insts out of emit order at %s (%s)" % (key, m["name"]))
        byname[m["name"]] = m
        for i, (kid, lg) in enumerate(zip(nd["kids"], nd["legs"])):
            k = "%s.%d" % (key, i)
            legs.append(dict(key=k, pts=lg["pts"], reps=take(len(lg["pts"]) - 2), src=m["out_net"], kid=kid))
            node(kid, k)
    node(d["tree"], "T")
    if next(it, None) is not None:
        raise ValueError("plan insts longer than its tree")
    top = d["tree"]
    root["src"] = rr[0]["in_net"] if rr else (byname[top["inst"]]["in_net"] if top["kind"] == "merge" else top["net"])
    for lg in legs:
        k = lg["kid"]
        lg["kid_in"] = byname[k["inst"]]["in_net"] if k["kind"] == "merge" else k["net"]
    return legs


def _same_pts(p, q):
    return len(p) == len(q) and all(abs(u[0] - v[0]) < 5e-4 and abs(u[1] - v[1]) < 5e-4 for u, v in zip(p, q))


def do_eco(a):
    """eco BUILT.json NEW.json ECO.tcl NEW_BUILT.json: ECO from the as-built trunk to a corr plan on the SAME topology.
    Only legs whose realised geometry changed are rebuilt (their repeaters removed, new ones created, the kid input
    re-attached); every other leg keeps its cells, names and nets, so an incremental clock GRT keeps their routes and
    the measured arrivals of unchanged legs are reproduced (corr then converges on deterministic arrivals).
    NEW_BUILT.json = NEW with the as-built names (the next corr/eco input)."""
    B = json.load(open(a.a1)); N = json.load(open(a.a2)); pre = a.prefix
    if has_icg(B["tree"]) or has_icg(N["tree"]):
        raise ValueError("eco: --ungated-split plans (ICG node in the tree) are not supported; rebuild with tcl")
    lb, ln = _legs(B, pre), _legs(N, pre)
    if [x["key"] for x in lb] != [x["key"] for x in ln]:
        raise ValueError("eco: topology differs (leg keys)")
    for x, y in zip(lb, ln):
        kx, ky = x["kid"], y["kid"]
        if kx["kind"] != ky["kind"] or (kx["kind"] != "merge" and kx["name"] != ky["name"]) or \
                not _same_pts([kx["p"]], [ky["p"]]):
            raise ValueError("eco: node differs at leg %s (corr keeps merge points and sinks)" % x["key"])
    tag = a.eco_tag or "e%d" % N["summary"].get("iteration", 0)
    used = {i["name"] for i in B["insts"]}
    cell = a.inv_cell
    kill, mk, attach, dead_nets = [], [], [], []
    kid_in = {}; n_new = 0; kept = changed = 0
    for x, y in zip(lb, ln):
        if _same_pts(x["pts"], y["pts"]):
            kept += 1
            y["as_reps"] = x["reps"]; kid_in[x["key"]] = x["kid_in"]
            continue
        changed += 1
        kill.extend(r["name"] for r in x["reps"])
        dead_nets.extend(r["out_net"] for r in x["reps"])
        net = x["src"]; reps = []
        for pt in y["pts"][1:-1]:
            nm = "%s_%s_r%d" % (pre, tag, n_new); n_new += 1
            if nm in used:
                raise ValueError("eco: new name %s already in the built trunk (use --eco-tag)" % nm)
            reps.append(dict(name=nm, cell=cell, p=list(pt), in_net=net, out_net=nm + "_o")); net = nm + "_o"
        mk.extend(reps); y["as_reps"] = reps; kid_in[x["key"]] = net
        k = x["kid"]
        if k["kind"] == "merge":
            attach.append(("merge", k["inst"], net))
        else:
            attach.append((k["kind"], k["name"], net))
    # as-built NEW: walk NEW's tree in emit order with the kept / new names
    bmerge = {}
    for x in lb:
        if x["kid"]["kind"] == "merge":
            bmerge[x["key"]] = x["kid"]["inst"]
    old = {i["name"]: i for i in B["insts"]}
    insts = []; sinks = []
    for x, y in zip(lb, ln):
        insts.extend(y["as_reps"])
        k = y["kid"]
        if k["kind"] == "merge":
            o = old[bmerge[x["key"]]]
            k["inst"] = o["name"]
            insts.append(dict(name=o["name"], cell=o["cell"], p=list(k["p"]), in_net=kid_in[x["key"]],
                              out_net=o["out_net"]))
        else:
            k["net"] = kid_in[x["key"]]
            sinks.append(dict(kind=k["kind"], name=k["name"], net=k["net"], p=k["p"]))
    # insts must be in emit order: re-walk to order them (merge inst precedes its legs' repeaters)
    order = []
    byn = {i["name"]: i for i in insts}
    rl = ln[0]
    order.extend(rl["as_reps"])

    def walk(nd, key):
        if nd["kind"] != "merge":
            return
        order.append(byn[nd["inst"]])
        for i in range(2):
            k = "%s.%d" % (key, i)
            order.extend(next(y for y in ln if y["key"] == k)["as_reps"])
            walk(nd["kids"][i], k)
    walk(N["tree"], "T")
    sink_order = {s["name"]: s for s in sinks}
    N["insts"] = order
    N["sinks"] = [sink_order[s["name"]] for s in N["sinks"]]
    eco = dict(built=a.a1, plan=a.a2, tag=tag, legs_kept=kept, legs_rebuilt=changed, cells_removed=len(kill),
               cells_added=len(mk), nets_removed=len(dead_nets))
    N["summary"]["eco"] = eco
    json.dump(N, open(a.out, "w"), indent=0)
    with open(a.a3, "w") as f:
        f.write("# parent_trunk_dme.py eco %s -> %s: %d legs kept, %d rebuilt\n" % (a.a1, a.a2, kept, changed))
        f.write("proc ptenv {k d} { if {[info exists ::env($k)] && $::env($k) ne \"\"} { return $::env($k) } ; return $d }\n"
                "set RS [ptenv ROOT_SUFFIX _root]; set RP [ptenv ROOT_PIN A]; set CP [ptenv CHILD_PIN clk]\n"
                "set blk [ord::get_db_block]; set db [ord::get_db]\n"
                "proc econet {n} { set b [ord::get_db_block]; set x [$b findNet $n]; if {$x eq \"NULL\"} { set x [odb::dbNet_create $b $n]; $x setSigType CLOCK }; return $x }\n")
        for n in kill:
            f.write("set i [$blk findInst {%s}]; if {$i eq \"NULL\"} { error \"eco: %s not found\" }; odb::dbInst_destroy $i\n" % (n, n))
        for r in mk:
            f.write("set m [$db findMaster %s]; set i [odb::dbInst_create $blk $m %s]; $i setLocation %d %d; "
                    "$i setPlacementStatus PLACED; [$i findITerm A] connect [econet %s]; [$i findITerm Y] connect [econet %s]\n"
                    % (r["cell"], r["name"], int(r["p"][0] * 1000), int(r["p"][1] * 1000), r["in_net"], r["out_net"]))
        for kind, name, net in attach:
            if kind == "merge":
                f.write("set it [[$blk findInst {%s}] findITerm A]\n" % name)
            elif kind == "cluster":
                f.write("set it [[$blk findInst [string cat {%s} $RS]] findITerm $RP]\n" % name)
            else:
                f.write("set it [[$blk findInst {%s}] findITerm $CP]\n" % name)
            f.write("$it disconnect; $it connect [econet %s]\n" % net)
        for n in dead_nets:
            f.write("set x [$blk findNet %s]; if {$x ne \"NULL\"} { if {[llength [$x getITerms]]} { error \"eco: net %s still connected\" }; odb::dbNet_destroy $x }\n" % (n, n))
        f.write("puts \"parent_trunk eco %s: %d legs kept, %d rebuilt, -%d/+%d cells\"\n" % (tag, kept, changed, len(kill), len(mk)))
    print(json.dumps(eco))
    return eco


def do_tcl(plan, out):
    d = json.load(open(plan)); s = d["summary"]
    with open(out, "w") as f:
        f.write("set ICG [list %.3f %.3f]\nset TI {}\nset TS {}\n" % tuple(s["icg"]["site"]))
        if "ungated_split" in s:         # opt-in: ICG inside the tree; the root leg starts on the clock port net
            u = s["ungated_split"]
            f.write("set ROOT_NET %s\nset ICG_IN %s\n" % (u["root_net"], u["icg_in"]))
        for i in d["insts"]:
            f.write("lappend TI [list %s %s %.3f %.3f %s %s]\n" % (i["name"], i["cell"], i["p"][0], i["p"][1],
                                                                  i["in_net"], i["out_net"]))
        for k in d["sinks"]:
            f.write("lappend TS [list %s {%s} %s]\n" % (k["kind"], k["name"], k["net"]))


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("mode", choices=["plan", "corr", "tcl", "ocv", "eco"])
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
    ap.add_argument("--topology", choices=["greedy", "bipart"], default="greedy",
                    help="plan: greedy bottom-up pairing (default, unchanged) or balanced top-down bipartition (opt-in)")
    ap.add_argument("--bipart-variants", default=None,
                    help="bipart: comma list of variants to try (top/rule/axis, e.g. type/delay/auto); default all")
    ap.add_argument("--bipart-pull", default="0,0.3",
                    help="bipart: merge-point pull toward the tile entry, ps/um (each value is one more variant)")
    ap.add_argument("--aocv-table", default=str(HERE / "clk_aocv_table_g021.json"),
                    help="bipart objective / ocv mode: approved clock AOCV table (12.4a b1, g 0.21 %%/mm)")
    ap.add_argument("--eco-tag", default=None, help="eco: name tag of the new repeaters (default e<iteration>)")
    ap.add_argument("--ungated-split", action="store_true",
                    help="plan (opt-in, QC-A0-KITS-9): geometry clusters flagged 'ungated' form a face branch merged "
                         "with the ICG-gated branch at the root (ICG node at the gated root + --icg-offset)")
    return ap


def main(argv=None):
    a = build_parser().parse_args(argv)
    if a.mode == "tcl":
        do_tcl(a.a1, a.a2)
        return 0
    if a.mode == "ocv":
        if a.a3 is None:
            raise SystemExit("ocv needs PLAN ARRIVALS_TT ARRIVALS_FF [OUT]")
        do_ocv(a)
        return 0
    if a.mode == "eco":
        if a.a3 is None or a.out is None:
            raise SystemExit("eco needs BUILT NEW ECO.tcl NEW_BUILT.json")
        do_eco(a)
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
