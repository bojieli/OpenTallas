"""clkplan driver: plan -> streets -> tree -> budgets / skew / crossings / tracks -> PASS/FAIL report + render.

    python3 -m clkplan.run PLAN.json --out OUTDIR [--model MODEL.json] [--leaf-um 300] [--no-streets] [--png]
"""
import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))          # opentools/
from common import plan as PL                          # noqa: E402

from . import analysis as AN                           # noqa: E402
from . import model as MD                              # noqa: E402
from . import streets as ST                            # noqa: E402
from . import tracks as TK                             # noqa: E402
from . import tree as TR                               # noqa: E402


def plan_streets(P, M, cfg):
    W, H = P["die"]["w"], P["die"]["h"]
    ko = PL.keepouts(P)
    isl = [tuple(r) for m in P["macros"] for r in (m.get("island_rects") or [])]
    sd = P.get("streets_config", {})
    return ST.Streets(W, H, ko, raster_um=sd.get("raster_um", M["raster_um"]), width_um=sd.get("width_um"),
                      demand=sd.get("demand", {}), reach_um=sd.get("reach_um", M["reach_um"]), islands=isl)


def analyse(P, M=None, cfg=None):
    t0 = time.time()
    M = M or MD.load()
    cfg = dict(cfg or {})
    W, H = P["die"]["w"], P["die"]["h"]
    S = None if cfg.get("no_streets") else plan_streets(P, M, cfg)
    sinks = PL.clock_sinks(P)
    T = TR.build(sinks, W, H, M, streets=S, entry=P["clock"].get("entry"),
                 cfg=dict(leaf_um=cfg.get("leaf_um"), leaf_sinks=cfg.get("leaf_sinks", 1), max_move_um=cfg.get("max_move_um"), frame=cfg.get("frame", "die")))
    ck = P["clock"]
    per = ck.get("period_ps") or 1000.0
    res = dict(plan=P.get("name"), schema=PL.SCHEMA, model=M["name"])
    res["streets"] = S.summary() if S is not None else None
    res["tree"] = TR.summary(T)
    res["unplaced"] = T.unplaced[:50]
    res["blocked_legs"] = [dict(name=lg["name"], level=lg["level"], len_um=lg["len_um"], blocked=lg["blocked"],
                                a=list(T.cells[lg["parent"]]["xy"]), b=list(T.cells[lg["child"]]["xy"]))
                           for lg in T.legs if any(b[2] > M["leg_max_um"] for b in lg["blocked"])]
    res["budgets"] = AN.budgets(T, ck.get("target_latency_ps"))
    res["region_skew"] = AN.region_skew(T)
    res["crossings"] = AN.crossings(T, M, P["crossings"], per, ck.get("min_crossing_margin_ps", 100.0),
                                    droop=cfg.get("droop", "regions"))
    res["tracks"] = TK.check(P, T, fill=cfg.get("fill", 0.6), bin_um=(S.width if S is not None else None))
    checks = []

    def chk(name, ok, detail):
        checks.append(dict(check=name, verdict="PASS" if ok else "FAIL", detail=detail))
    if S is not None:
        s = res["streets"]
        chk("street_reach", s["macros_over_reach"] == 0, f"{s['macros_over_reach']}/{s['macros']} hard macros farther than "
            f"{s['reach_um']} um from a street")
        chk("street_width", s["width_um"] + 1e-6 >= s["required_width_um"],
            f"street width {s['width_um']} vs required {s['required_width_um']} um")
    t = res["tree"]
    chk("clock_leg_sites", t["blocked_legs"] == 0, f"{t['blocked_legs']} legs with a gap between legal repeater sites > "
        f"{M['leg_max_um']} um (spans {t['blocked_span_um']})")
    chk("clock_node_sites", t["unplaced"] == 0, f"{t['unplaced']} tree nodes with no legal site within "
        f"{T.cfg['max_move_um']} um")
    cs = res["crossings"]["summary"]
    chk("crossing_margin", cs["fail"] == 0 and cs["errors"] == 0,
        f"{cs['fail']}/{cs['landed']} landed crossings under {cs['min_margin_ps']} ps derated phase margin"
        + "".join(f"; {c} worst {cs[c]['worst_margin_ps']} ps, max unshared {cs[c]['max_unshared_ps']} ps"
                  for c in ("TT", "FF") if c in cs and cs[c]["worst_margin_ps"] is not None))
    tf = res["tracks"]["fails"]
    chk("top_metal_tracks", not tf, "; ".join(tf) if tf else res["tracks"].get("note", "every clock bin within supply"))
    res["checks"] = checks
    res["verdict"] = "PASS" if all(c["verdict"] == "PASS" for c in checks) else "FAIL"
    res["sec"] = round(time.time() - t0, 1)
    return res, T, S


def write_schema_outputs(P, res, T):
    """the outputs other tools consume, written back into the plan (schema sections clock_plan / crossings)."""
    Q = json.loads(json.dumps(P))
    Q["clock_plan"] = dict(tool="opentools.clkplan", verdict=res["verdict"],
                           target_latency_ps=res["budgets"]["target_latency_ps"],
                           taps=[dict(sink=r["sink"], tap_target_ps=r["tap_target_ps"], tree_arrival_ps=r["tree_arrival_ps"],
                                      balance_ps=r["balance_ps"]) for r in res["budgets"]["rows"]],
                           streets=res["streets"], tree=res["tree"])
    by = {(r["a"], r["b"]): r for r in res["crossings"]["rows"] if "error" not in r}
    for x in Q["crossings"]:
        r = by.get((x["a"], x["b"]))
        if r:
            x["derated_margin_ps"] = {c: r[c]["margin_ps"] for c in ("TT", "FF") if c in r}
            x["unshared_ps"] = {c: max(r[c]["unshared_a_ps"], r[c]["unshared_b_ps"]) for c in ("TT", "FF") if c in r}
            x["margin_pass"] = r["pass"]
    return Q


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--out", required=True)
    ap.add_argument("--model")
    ap.add_argument("--leaf-um", type=float)
    ap.add_argument("--max-move-um", type=float)
    ap.add_argument("--leaf-sinks", type=int, default=1, help="stop bisecting a box with <= this many sinks (0 = full depth)")
    ap.add_argument("--frame", default="die", choices=["die", "sinks"])
    ap.add_argument("--droop", default="regions", choices=["regions", "always"])
    ap.add_argument("--no-streets", action="store_true")
    ap.add_argument("--png", action="store_true")
    a = ap.parse_args(argv)
    P = PL.load(a.plan)
    M = MD.load(a.model)
    res, T, S = analyse(P, M, dict(leaf_um=a.leaf_um, leaf_sinks=a.leaf_sinks, max_move_um=a.max_move_um, frame=a.frame, droop=a.droop,
                                   no_streets=a.no_streets))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "clkplan_report.json").write_text(json.dumps(res, indent=1, default=str) + "\n")
    PL.save(write_schema_outputs(P, res, T), out / "plan_out.json")
    from . import report as RP
    (out / "clkplan_report.md").write_text(RP.markdown(res))
    if a.png:
        from . import render as RD
        RD.render(P, res, T, S, out / "clkplan.png")
    print(f"{res['plan']}: {res['verdict']} in {res['sec']} s")
    for c in res["checks"]:
        print(f"  {c['verdict']:4s} {c['check']}: {c['detail']}")
    return 0 if res["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
