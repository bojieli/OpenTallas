#!/usr/bin/env python3
"""MODEL-REFIT-3 (2026-10-26): uf_phys v3 = the MODEL-REFIT-2 physical kernel (uf_phys.py, unchanged) plus three terms,
each a calibration parameter or a textbook constant, never a per-build offset (METHODOLOGY 12.8):

  T7 PER-STAGE TERM KSTAGE (ps, one value per analysis): added to every buffer stage's NLDM delay. The refit4 residual
     tracked stages per path (-5.4/-4.4/+0.9/+4.8 ps at 5/6/8/9 stages, QC-SU-PROG-L2); a constant per stage is the
     simplest physical form (NLDM interpolation / pin-slew error that repeats at every stage).
  T8 VIA RESISTANCE (RCX basis only): a net with n routed vias gets n * RVIA * KVIA extra series resistance, spread
     uniformly over its wire (r_eff = r + n*RVIA*KVIA / L_net).  RVIA = setRC.tcl V1-V5 mean (0.0172 V1-V3, 0.0118 V4-V5
     kOhm; the M3/M4 jog ladders use V3+V4 -> 0.0145).  GRT RC (estimate_parasitics, rc_cal 0.8/0.9) sees almost none of
     these vias, so the GRT basis uses n = 0.  QC-SU-F4A-SIGN: long M4 island feeds DRT-routed with 78-100 vias arrive
     30-41 ps late at RCX.  The via count per leg is a PLAN INPUT (layer/route plan: VIAS dict net -> n); legs the plan
     does not state get the clean-leg default VIA_DEFAULT(L) and are listed as unplanned (gate: ladder-risk legs).
  T9 GRT->RCX WIRE SCALE (RCX basis only): KR_RCX, KC_RCX multiply the GRT-basis wire r, c (rc_cal 0.8/0.9 is a GRT
     calibration; extracted SPEF differs).  Fitted only on points that have both GRT and RCX measurements.
  T10 LEAF-NET WIRE FACTOR BLEAF (fit, both analyses separately): the leaf net Elmore is taken on a driver-rooted
     Prim MST x KLEAF; GRT/DRT build a Steiner tree with shorter driver->sink paths, and 30-46% of leaf wire is on M4/M5
     (routed census, vias_rcx.tsv), not M2/M3.  BLEAF scales the leaf-net wire delay (uf_phys used BETA for it).
     Found from the S81-HEAD calibration: leaf stage error correlates with leaf MST (r -0.44 HEAD cal1, leaf-stage
     delay r -0.74 btab_r5) = the 1.6-1.9x window over-prediction.
Basis is explicit: basis="GRT" (n_via=0, KR=KC=1) or basis="RCX".  PLAN MODEL, UNCHECKED until NUMBER-CHECK.
"""
import gzip
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "model_refit2_1026" / "py"))
import common  # noqa: E402
import uf_phys as U  # noqa: E402

_open = open


def gzopen(p, mode="r", *a, **k):
    p = str(p)
    if not Path(p).exists() and Path(p + ".gz").exists():
        p = p + ".gz"
    if p.endswith(".gz"):
        return gzip.open(p, "rt")
    return _open(p, mode, *a, **k)


common.open = gzopen        # common.parse_* read .gz transparently
U.common.open = gzopen

RVIA = 0.0145               # kOhm per via (setRC.tcl V3/V4 mean)
VIA_DEFAULT_PER_UM = 0.0    # clean legs: vias are at the ends only (layer changes), modelled by VIA_DEFAULT_ENDS
VIA_DEFAULT_ENDS = 12       # clean-leg via count (F4A routed clean legs 8-22 vias at 37-74 um; median used, UNCHECKED)


def load_plan(spec, geo, seg_json):
    import json
    seg = json.load(gzopen(seg_json)).get("seg_um", {}) if seg_json else {}
    return U.Plan(spec, geo, seg)


def depth(plan):
    """buffer stages from root to each leaf/macro stage (root counts as 1, the leaf cell counts)."""
    d = {"root": 1}
    order = ["root"]
    i = 0
    while i < len(order):
        for c in plan.kids.get(order[i], []):
            d[c] = d[order[i]] + 1
            order.append(c)
        i += 1
    return d


def net_name(drv):
    return "ot_ms_root_n" if drv == "root" else f"ot_ms_{drv}_n"


def predict3(plan, LIBS, corner, alpha=0.0, beta=1.0, kleaf=1.25, s_root=0.0, edge="rise", gslew=U.LN9, kstage=0.0,
             basis="GRT", kr=1.0, kc=1.0, kvia=1.0, vias=None, bleaf=None, detail=None):
    """uf_phys.predict with T7-T10 (bleaf None = beta, i.e. uf_phys).  vias: dict net name -> routed/planned via count (RCX basis only)."""
    L = LIBS[corner]
    dk, sk = (("rise", "trise") if edge == "rise" else ("fall", "tfall"))
    rcx = basis == "RCX"
    if not rcx:
        kr = kc = 1.0
        vias = None
    vias = vias or {}
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
            cpin = v["cpin"][corner] if "cpin" in v else (U.FFC[corner] if v["kind"] == "leaf" else U.MACRO_CK)
            E = [(a, b, U.man(P[a], P[b]) * kleaf) for a, b in U.mst_edges(P)]
            ln = sum(e[2] for e in E)
            r23 = U.R23 * kr
            if rcx and v["kind"] == "leaf" and ln > 0:
                r23 += vias.get(f"ot_ms_{n}_clk", 0) * RVIA * kvia / ln
            Cw, Cp, el, Rw = U.rc_tree(P, E, {k: cpin for k in range(1, len(P))}, r23, U.C23 * kc)
            sh = U._shield(Lc, dk, s0, Cw + Cp, Rw)
            C = Cp + Cw * (1 - alpha * sh)
            d = U.interp(Lc[dk], s0, C) + kstage
            sink_arrivals = [t0 + d + (beta if bleaf is None else bleaf) * el[k] for k in range(1, len(P))]
            out[n] = sum(sink_arrivals) / len(sink_arrivals)
            if detail is not None:
                detail[n] = dict(sinks=sink_arrivals, slew_in=s0,
                                 slew_out=U.interp(Lc[sk], s0, C))
            continue
        net = plan.nets[n]
        pts, E = net["pts"], net["edges"]
        ch = plan.kids[n]
        pincap = {net["pin"][c]: L[plan.nodes[c]["cell"]]["cin"] for c in ch}
        ln = sum(e[2] for e in E)
        r45 = U.R45 * kr
        if rcx and ln > 0:
            r45 += vias.get(net_name(n), 0) * RVIA * kvia / ln
        Cw, Cp, el, Rw = U.rc_tree(pts, E, pincap, r45, U.C45 * kc)
        sh = U._shield(Lc, dk, s0, Cw + Cp, Rw)
        C = Cp + Cw * (1 - alpha * sh)
        d = U.interp(Lc[dk], s0, C) + kstage
        so = U.interp(Lc[sk], s0, C)
        for c in ch:
            e = el[net["pin"][c]]
            s1 = math.sqrt(so * so + (gslew * e) ** 2)
            arr[c] = (t0 + d + beta * e, s1)
    return out, arr


def basis_leaf(plan, LIBS, corner, kind, p, basis="GRT", vias=None):
    """kind 'max' -> TT/FF arrival_max_rise; 'min' -> early = min(rise, fall) of the min analysis."""
    q = dict(p)
    if kind == "max":
        r, _ = predict3(plan, LIBS, corner, edge="rise", basis=basis, vias=vias, **q)
        return r
    r, _ = predict3(plan, LIBS, corner, edge="rise", basis=basis, vias=vias, **q)
    f, _ = predict3(plan, LIBS, corner, edge="fall", basis=basis, vias=vias, **q)
    return {k: min(r[k], f[k]) for k in r}


def plan_vias(plan, planned=None, ladder_um=30.0):
    """predicted via count per tree net from the layer/route plan: planned[net] if stated, else VIA_DEFAULT_ENDS
    (clean leg).  Returns (vias, unplanned_long) where unplanned_long lists nets with a leg > ladder_um that the plan
    did not pin to a PG-via-free track (GEOM-REVIEW-7: those are the ladder-risk legs; gate reports them)."""
    planned = planned or {}
    out, risk = {}, []
    for drv in plan.kids:
        nm = net_name(drv)
        lmax = max((plan._seglen(c) for c in plan.kids[drv]), default=0.0)
        if nm in planned:
            out[nm] = planned[nm]
        else:
            out[nm] = VIA_DEFAULT_ENDS
            if lmax > ladder_um:
                risk.append((nm, round(lmax, 1)))
    return out, risk
