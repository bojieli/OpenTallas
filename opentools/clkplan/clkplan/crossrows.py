"""Crossing margins from EXTERNAL per-crossing timing rows (routed-clock STA), in any clkplan crossing mode.

    python3 -m clkplan.crossrows ROWS.json [--corners TT_x,FF_y] [--crossing-mode count_aligned|ring_phase|phase]
                                [--no-spice-scale] [--period 833] [--aperture T/8] [--wander-frac 0.05]
                                [--origin-cycles PLAN.json] [--out JSON]

ROWS.json ('crossing timing rows', e.g. the output of a landed-phase OCV pass on a routed die clock):
    {"corners": {<corner key>: {"all": [{port, src, dst, d_ps, p_up_ps, p_dn_ps, unshared_a_ps?, unshared_b_ps?}]}}}
  d = nominal capture - launch clock latency, p_up / p_dn = derated growth / shrink of d on the unshared clock.
  The corner key's prefix before '_' (TT / FF / SS) selects the spice calibration factor.
SPICE-SCALED by default: rows are STA-basis, so d, p_up, p_dn and unshared are multiplied by model.spice_cal[corner]
(all are linear in the clock-branch delays; the OCV fractions depend on stage count / distance only).
--origin-cycles: a JSON {"crossings": [{port, origin_cycles [X, Y]}]} or count_align_plan output (L_lo / K_eff / wander
are used to recover X, Y) giving the start-tree whole-cycle ambiguity per crossing (default 0, 0).
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))

from . import model as MD   # noqa: E402
from . import ocv           # noqa: E402


def load_rows(d, corners):
    by = {}
    for ck in corners:
        for r in d["corners"][ck]["all"]:
            by.setdefault(r["port"], {})[ck] = r
    return {p: v for p, v in by.items() if len(v) == len(corners)}


def evaluate(by, corners, M, T=833.0, mode="count_aligned", ap=None, wander_frac=0.05, origin=None, depths=ocv.CA_DEPTHS):
    out = []
    for port, v in by.items():
        trip, uns, r0 = {}, 0.0, v[corners[0]]
        for ck in corners:
            r = v[ck]
            s = M.arrival_scale(ck.split("_")[0], "sta")
            trip[ck] = (r["d_ps"] * s, r["p_up_ps"] * s, r["p_dn_ps"] * s)
            uns = max(uns, r.get("unshared_a_ps", 0.0) * s, r.get("unshared_b_ps", 0.0) * s)
        o = dict(port=port, src=r0.get("src"), dst=r0.get("dst"))
        if mode == "count_aligned":
            ca = ocv.count_aligned_margin(trip, T, ap, depths=depths, origin_cycles=(origin or {}).get(port, (0, 0)),
                                          wander_ps=wander_frac * uns)
            o.update(K=ca["K"], depth=ca["depth"], latency_cycles=ca["latency_cycles"], L_lo_ps=round(ca["L_lo_ps"], 1),
                     L_hi_ps=round(ca["L_hi_ps"], 1), margin_lo_ps=round(ca["margin_lo_ps"], 1),
                     margin_hi_ps=round(ca["margin_hi_ps"], 1), margin_ps=round(ca["margin_ps"], 1),
                     wander_ps=round(wander_frac * uns, 1), origin_cycles=list(ca["origin_cycles"]))
        elif mode == "ring_phase":
            apc = M.m.get("capture_aperture_ps") or {}
            rp = ocv.ring_phase_margin(trip, T, {ck: float(apc.get(ck.split("_")[0], 0.0)) for ck in corners})
            o.update(K=rp["K"], margin_ps=round(rp["margin_ps"], 1))
        else:
            o.update(margin_ps=round(min(T / 2 - max(abs(d + pu), abs(d - pd)) for d, pu, pd in trip.values()), 1))
        out.append(o)
    return out


def origin_from(path, T=833.0):
    d = json.loads(Path(path).read_text())
    res = {}
    for o in d.get("crossings", []):
        if "origin_cycles" in o:
            res[o["port"]] = tuple(o["origin_cycles"])
        elif o.get("path_ambiguous_cycles") and o.get("L_lo_ps") is not None and o.get("kind") == "nontree":
            # count_align_plan: rel_lo = lo + amb_lo T - w = L_lo - K_eff T
            lo = o["d_ps"] - o["p_dn_ps"]
            X = -round((o["L_lo_ps"] - o["K_eff"] * T + o["wander_ps"] - lo) / T)
            res[o["port"]] = (X, o["path_ambiguous_cycles"] - X)
    return res


def summary(out, mm=100.0):
    ok = [o for o in out if o.get("margin_ps") is not None and o.get("depth", 4)]
    s = dict(crossings=len(out), fail=sum(1 for o in out if o.get("depth", 4) is None or o["margin_ps"] < mm),
             worst_margin_ps=min((o["margin_ps"] for o in ok), default=None))
    if out and "depth" in out[0]:
        s.update(depth4=sum(o["depth"] == 4 for o in out), depth8=sum(o["depth"] == 8 for o in out),
                 worst_margin_lo_ps=min((o["margin_lo_ps"] for o in ok), default=None),
                 worst_margin_hi_ps=min((o["margin_hi_ps"] for o in ok), default=None),
                 lat_hist={str(k): sum(1 for o in ok if o["latency_cycles"] == k)
                           for k in sorted({o["latency_cycles"] for o in ok})})
    return s


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rows")
    ap.add_argument("--corners", default="TT_droop-regions_corelat250,FF_droop-regions_corelat202.5")
    ap.add_argument("--crossing-mode", default="count_aligned", choices=["count_aligned", "ring_phase", "phase"])
    ap.add_argument("--no-spice-scale", action="store_true")
    ap.add_argument("--model")
    ap.add_argument("--period", type=float, default=833.0)
    ap.add_argument("--aperture", type=float, help="count_aligned guard-edge aperture (default T/8)")
    ap.add_argument("--wander-frac", type=float, default=0.05)
    ap.add_argument("--min-margin", type=float, default=100.0)
    ap.add_argument("--origin-cycles")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    M = MD.load(a.model, spice_scale=not a.no_spice_scale)
    cs = a.corners.split(",")
    by = load_rows(json.loads(Path(a.rows).read_text()), cs)
    org = origin_from(a.origin_cycles, a.period) if a.origin_cycles else None
    out = evaluate(by, cs, M, a.period, a.crossing_mode, a.aperture, a.wander_frac, org)
    s = summary(out, a.min_margin)
    s.update(mode=a.crossing_mode, spice_cal=M.m.get("spice_cal"), corners=cs, period_ps=a.period, source=a.rows)
    print(json.dumps(s, indent=1))
    if a.out:
        Path(a.out).write_text(json.dumps(dict(summary=s, crossings=out), indent=0) + "\n")
    return 0 if s["fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
