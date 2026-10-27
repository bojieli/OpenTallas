#!/usr/bin/env python3
"""MODEL-REFIT-2 (2026-10-26): physical as-built clock-latency model for plan-built mscts_h trees (QC SU kits).

Replaces the uf_asbuilt.py timing kernel (same plan inputs: the mscts_h spec actually built, the placement geo, and
uf_asbuilt's maze segment lengths seg_um).  What changed, each one a physical term (no constant offset):
  T1 NET TOPOLOGY: a driver with fo>1 branches drives ONE rectilinear Steiner tree (what GRT builds), not fo separate
     star wires.  uf_asbuilt loaded the driver with the SUM of branch wires (root fo6: 480 um modelled vs ~176 um of
     wire measured from the GRT net cap) -> every fanout stage too slow.  Here: iterated 1-Steiner on the Hanan grid,
     Manhattan, driver-rooted; edges scaled by the net's maze/Manhattan detour where a branch must go round a macro;
     wire delay = Elmore on that tree (shared trunk carries downstream cap).  2-pin nets = maze length (as before).
  T2 MACRO LEAF STAGES on the B nets (mscts_h hangs one leaf-cell per SRAM clock pin on the leaf's input net): cin + wire
     are now part of that B net's load; the macro pin cap is read from the geo/macro lib value given (CK_MACRO_FF).
  T3 SLEW: the root input slew is the SDC port slew (0 ps measured at ot_ms_root/A), not an ideal 20 ps; the slew at a
     child pin = sqrt(s_drv^2 + (ln9 * Elmore_w)^2) (wire slew degradation, PERI form), used for the child stage.
  T4 LEAF NET: leaf wire = MST x KLEAF (GRT pin-access/gcell overhead on the M2/M3 leaf nets; KLEAF from measured leaf
     net wire cap / (c x MST)), r of the leaf layers (M2/M3 average x rc_cal), Elmore to the mean sink radius.
  T5 EFFECTIVE CAP (fit parameter ALPHA, both corners, one value): the driver NLDM load = pin caps + c*wire*(1-ALPHA*sh),
     sh = Rw/(Rw+Rd) resistive shielding of the net (Rw = Elmore-weighted wire R, Rd = NLDM dDelay/dC of the cell).
  T6 WIRE DELAY FACTOR (fit parameter BETA): 50% delay of the distributed wire = BETA x Elmore (step: 0.69 lumped /
     0.38/0.5 distributed; ramp inputs push it toward 1).
Fit: ALPHA, BETA only (shared TT/FF, shared by every build), on per-LEAF mean arrival; leave-one-build-out validation.
PLAN MODEL, UNCHECKED.
"""
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common  # noqa: E402

RC = {"M2": (2.97127e-2, 1.74942e-1), "M3": (3.12870e-2, 1.55554e-1), "M4": (1.80365e-2, 1.78475e-1),
      "M5": (1.89935e-2, 1.64264e-1)}
KR, KC = 0.8, 0.9                                     # OT_RC_CAL 0.8,0.9 (the measured basis)
R45 = 0.5 * (RC["M4"][0] + RC["M5"][0]) * KR          # tree legs: M4/M5 (same as uf_asbuilt)
C45 = 0.5 * (RC["M4"][1] + RC["M5"][1]) * KC
R23 = 0.5 * (RC["M2"][0] + RC["M3"][0]) * KR          # leaf nets: M2/M3
C23 = 0.5 * (RC["M2"][1] + RC["M3"][1]) * KC
FFC = {"TT": 0.4132, "FF": 0.4634}                      # register CLK pin cap per sink, report_net pin cap / n (all 3 builds, both corners agree to 1e-4); uf_asbuilt 0.4747/0.5220 was high
MACRO_CK = 9.3458                                      # SRAM clk pin cap (report_net, TT; same lib both corners here)
LN9 = math.log(9.0)
SIZES = ["BUFx8_ASAP7_75t_R", "BUFx10_ASAP7_75t_R", "BUFx12f_ASAP7_75t_R", "BUFx16f_ASAP7_75t_R", "BUFx24_ASAP7_75t_R",
         # QC-SU-PROG-L2: parsed for the 4th fit build (prog k5 uses BUFx4/BUFx6f); the calibrated SIZER range is phys_gate's call
         "BUFx4_ASAP7_75t_R", "BUFx4f_ASAP7_75t_R", "BUFx5_ASAP7_75t_R", "BUFx6f_ASAP7_75t_R"]


def interp(tab, s, C):
    i1, i2, v = tab

    def idx(a, x):
        for k in range(len(a) - 1):
            if x <= a[k + 1]:
                return k
        return len(a) - 2
    a, b = idx(i1, s), idx(i2, C)
    ta = (s - i1[a]) / (i1[a + 1] - i1[a])
    tb = (C - i2[b]) / (i2[b + 1] - i2[b])
    return v[a][b] * (1 - ta) * (1 - tb) + v[a + 1][b] * ta * (1 - tb) + v[a][b + 1] * (1 - ta) * tb + v[a + 1][b + 1] * ta * tb


def man(p, q):
    return abs(p[0] - q[0]) + abs(p[1] - q[1])


def mst_edges(P):
    n = len(P)
    inn = [False] * n
    dd = [1e18] * n
    par = [-1] * n
    dd[0] = 0
    E = []
    for _ in range(n):
        u = min((i for i in range(n) if not inn[i]), key=lambda i: dd[i])
        inn[u] = True
        if par[u] >= 0:
            E.append((par[u], u))
        for v in range(n):
            if not inn[v]:
                e = man(P[u], P[v])
                if e < dd[v]:
                    dd[v], par[v] = e, u
    return E


def mst_len(P):
    return sum(man(P[a], P[b]) for a, b in mst_edges(P))


def steiner(P):
    """iterated 1-Steiner (Kahng-Robins) on the Hanan grid; returns points (pins first) + MST edges."""
    pts = list(P)
    best = mst_len(pts)
    while True:
        xs = sorted({p[0] for p in pts})
        ys = sorted({p[1] for p in pts})
        cand = None
        for x in xs:
            for y in ys:
                q = (x, y)
                if q in pts:
                    continue
                l_ = mst_len(pts + [q])
                if l_ < best - 1e-6:
                    best, cand = l_, q
        if cand is None:
            break
        pts.append(cand)
    # drop Steiner points of degree <= 2 is not needed for Elmore (degree-2 points are just bends)
    return pts, mst_edges(pts)


def load_libs(libdir, libpy=None):
    sys.path.insert(0, str(libpy or Path(__file__).parent))
    import lib  # the su_tree lib.py parser (same NLDM tables as uf_asbuilt)
    return {k: lib.cells(str(Path(libdir) / f"invbuf_{k.lower()}.lib"), SIZES) for k in ("TT", "FF")}


class Plan:
    def __init__(self, spec, geo, seg_um):
        S = common.parse_spec(spec)
        sinks, macs, entry = common.parse_geo(geo)
        self.nodes = {"root": dict(par=None, xy=S["root"], cell="BUFx24_ASAP7_75t_R", kind="root")}
        for n, v in S["tree"].items():
            self.nodes[n] = dict(par=v["par"], xy=v["xy"], cell=v["cell"], kind="node")
        for n, v in S["leaves"].items():
            self.nodes[n] = dict(par=v["par"], xy=v["xy"], cell=v["cell"], kind="leaf",
                                 sinks=[sinks[r] for r in v["regs"]])
        for k, m in enumerate(S["macros"]):     # mscts_h: macro leaf stage on the input net of leaf m["leaf"]
            lp = S["leaves"][m["leaf"]]
            pin = macs[m["inst"]]["pin"]
            self.nodes[f"m{k}"] = dict(par=lp["par"], xy=m["xy"], cell=lp["cell"], kind="macro", sinks=[pin],
                                       inst=m["inst"])
        self.seg = seg_um
        self.kids = {}
        for n, v in self.nodes.items():
            if v["par"]:
                self.kids.setdefault(v["par"], []).append(n)
        self.nets = {d: self._net(d, ch) for d, ch in self.kids.items()}

    def _seglen(self, n):
        if n in self.seg:
            return self.seg[n]
        v = self.nodes[n]
        return man(v["xy"], self.nodes[v["par"]]["xy"])

    def _net(self, drv, ch):
        """returns list of edges (a, b, length) rooted at 0 = driver, and pin index of each child."""
        d = self.nodes[drv]["xy"]
        if len(ch) == 1:
            return dict(pts=[d, self.nodes[ch[0]]["xy"]], edges=[(0, 1, self._seglen(ch[0]))], pin={ch[0]: 1})
        P = [d] + [self.nodes[c]["xy"] for c in ch]
        pts, E = steiner(P)
        # detour scale: maze length / Manhattan per child (macro walls); applied to the tree as the load-weighted mean
        sc = []
        for c in ch:
            mh = man(d, self.nodes[c]["xy"])
            sc.append(max(1.0, self._seglen(c) / mh) if mh > 1 else 1.0)
        f = sum(sc) / len(sc)
        return dict(pts=pts, edges=[(a, b, man(pts[a], pts[b]) * f) for a, b in E],
                    pin={c: i + 1 for i, c in enumerate(ch)}, detour=f)


def predict(plan, LIBS, corner, alpha=0.0, beta=1.0, kleaf=1.25, s_root=0.0, edge="rise", gslew=LN9):
    """per-node input arrival for one transition edge through non-inverting buffers; returns leaf mean arrivals."""
    L = LIBS[corner]
    dk, sk = (("rise", "trise") if edge == "rise" else ("fall", "tfall"))
    arr = {"root": (0.0, s_root)}
    out = {}
    order = ["root"]
    i = 0
    while i < len(order):
        order += plan.kids.get(order[i], [])
        i += 1
    for n in order:
        v = plan.nodes[n]
        t0, s0 = arr[n]
        Lc = L[v["cell"]]
        if v["kind"] in ("leaf", "macro"):
            P = [v["xy"]] + list(v["sinks"])
            cpin = FFC[corner] if v["kind"] == "leaf" else MACRO_CK
            E = [(a, b, man(P[a], P[b]) * kleaf) for a, b in mst_edges(P)]
            Cw, Cp, el, Rw = rc_tree(P, E, {i: cpin for i in range(1, len(P))}, R23, C23)
            sh = _shield(Lc, dk, s0, Cw + Cp, Rw)
            C = Cp + Cw * (1 - alpha * sh)
            d = interp(Lc[dk], s0, C)
            out[n] = t0 + d + beta * sum(el[i] for i in range(1, len(P))) / (len(P) - 1)
            continue
        net = plan.nets[n]
        pts, E = net["pts"], net["edges"]
        ch = plan.kids[n]
        pincap = {net["pin"][c]: L[plan.nodes[c]["cell"]]["cin"] for c in ch}
        Cw, Cp, el, Rw = rc_tree(pts, E, pincap, R45, C45)
        sh = _shield(Lc, dk, s0, Cw + Cp, Rw)
        C = Cp + Cw * (1 - alpha * sh)
        d = interp(Lc[dk], s0, C)
        so = interp(Lc[sk], s0, C)
        for c in ch:
            e = el[net["pin"][c]]
            s1 = math.sqrt(so * so + (gslew * e) ** 2)
            arr[c] = (t0 + d + beta * e, s1)
    return out, arr


def rc_tree(pts, E, pincap, r, c):
    """driver-rooted RC tree (node 0 = driver): total wire C, pin C, Elmore to every node, Elmore-weighted wire R."""
    adj = {}
    for a, b, l_ in E:
        adj.setdefault(a, []).append((b, l_))
        adj.setdefault(b, []).append((a, l_))
    parent, plen, ordr = {0: None}, {0: 0.0}, [0]
    for u in ordr:
        for w, l_ in adj.get(u, []):
            if w not in parent:
                parent[w], plen[w] = u, l_
                ordr.append(w)
    kids = {}
    for u in ordr[1:]:
        kids.setdefault(parent[u], []).append(u)
    down = {}
    for u in reversed(ordr):
        down[u] = pincap.get(u, 0.0) + sum(down[w] + c * plen[w] for w in kids.get(u, []))
    Cw = c * sum(l_ for _, _, l_ in E)
    Cp = sum(pincap.values())
    el = {0: 0.0}
    for u in ordr[1:]:
        el[u] = el[parent[u]] + r * plen[u] * (c * plen[u] / 2 + down[u])
    Rw = sum(r * plen[u] * (down[u] + c * plen[u] / 2) for u in ordr[1:]) / max(Cw + Cp, 1e-9)
    return Cw, Cp, el, Rw


def _shield(Lc, dk, s0, C, Rw):
    """resistive shielding fraction Rw/(Rw+Rd); Rd = NLDM slope dDelay/dC around C."""
    dC = max(1.0, 0.1 * C)
    Rd = (interp(Lc[dk], s0, C + dC) - interp(Lc[dk], s0, max(0.1, C - dC))) / (C + dC - max(0.1, C - dC))
    return Rw / (Rw + Rd) if Rw + Rd > 0 else 0.0


def leaf_basis(plan, LIBS, corner, pmax, pmin):
    """measurement bases (meas_ck.tcl): 'rise' = arrival_max_rise, 'late' = max(rise, fall) max analysis,
    'early' = min(rise, fall) of the MIN analysis.  OpenSTA's min analysis on the same estimated parasitics gives
    smaller wire delay/slew (measured min/max wire ratio 0.86-0.89, cell 0.95-0.96 on all 3 builds), so the max and min
    analyses carry their own wire terms pmax / pmin = dict(alpha, beta, gslew)."""
    r, _ = predict(plan, LIBS, corner, edge="rise", **pmax)
    f, _ = predict(plan, LIBS, corner, edge="fall", **pmax)
    rm, _ = predict(plan, LIBS, corner, edge="rise", **pmin)
    fm, _ = predict(plan, LIBS, corner, edge="fall", **pmin)
    return dict(rise=r, late={k: max(r[k], f[k]) for k in r}, early={k: min(rm[k], fm[k]) for k in r})
