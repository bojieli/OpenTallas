#!/usr/bin/env python3
"""CA-OCV-1 cross-die sweep (estimate-only, no builds): the count-aligned row of die_sta_related (claude/ca-ocv-1-1028)
on one die's current gate inputs, with and without the class clock variation term.
usage: ca_sweep.py TOOLS PROOF PLAN BIND REG_JSON OUT.json [--no-cppr-lca] [--core-ff 202.5] [--droop-regions F]
REG_JSON = an existing die_sta_related.json of the same proof (its corners[C].register = pin-register arcs)."""
import argparse
import json
import sys
from pathlib import Path

ap = argparse.ArgumentParser()
for k in ("tools", "proof", "plan", "bind", "reg", "out"):
    ap.add_argument(k)
ap.add_argument("--no-cppr-lca", action="store_true")
ap.add_argument("--core-ff", type=float, default=202.5)
ap.add_argument("--droop-regions")
ap.add_argument("--need", type=float, default=100.0)
a = ap.parse_args()
sys.path.insert(0, a.tools)
import die_sta_related as D  # noqa: E402

proof = Path(a.proof)
plan = json.loads(Path(a.plan).read_text())
bind = json.loads(Path(a.bind).read_text())
regsrc = json.loads(Path(a.reg).read_text())
dr = a.droop_regions or (str(proof / "droop_regions.json") if (proof / "droop_regions.json").exists() else None)
lat_tt = float(plan.get("clock", {}).get("common_latency_ps", 250.0))
res = dict(proof=str(proof), plan=a.plan, bind=a.bind, droop_regions=dr, clock_cal="spice", key="region",
           core_latency_ps=dict(TT=lat_tt, FF=a.core_ff), corners={})
for c in ("TT", "FF"):
    meta, taps = D.load_taps(proof, c)
    lca = (not a.no_cppr_lca) and all("tree_path" in t for t in taps.values())
    D.CPPR_LCA = lca
    meta, taps = D.scale_clock(meta, taps, D.SPICE_CLOCK_CAL[c])
    rng = meta["cppr_node_range_ps"]
    pairs, _ = D.build_pairs(plan, taps)
    reg = regsrc["corners"][c]["register"]
    lat = lat_tt if c == "TT" else a.core_ff
    try:
        ocv = D.ca_ocv(proof, meta, taps, c, lat, "table", "shared", "mesh", dr)
        err = None
    except SystemExit as e:
        ocv, err = None, str(e)
    A = D.count_align_landed(pairs["landed"], taps, bind, D.PERIOD_PS, reg, need_ps=a.need, cppr_range=rng, key="region")
    B = D.count_align_landed(pairs["landed"], taps, bind, D.PERIOD_PS, reg, need_ps=a.need, cppr_range=rng, key="region",
                             ocv=ocv, ocv_label="table/shared") if ocv else None

    def summ(r):
        w = sorted(r["rows"], key=lambda x: min(x["margin_lo_ps"], x["margin_hi_ps"]))
        return dict(verdict=r["verdict"], crossings=r["crossings"], sta_timed=r["sta_timed"], unbound=r["unbound"],
                    no_taps=r["no_taps"], fail_lt_need=r["fail"], below_need=r["below_need"],
                    worst_lo=r["worst_lo"] and r["worst_lo"]["margin_lo_ps"], worst_lo_port=r["worst_lo"] and r["worst_lo"]["port"],
                    worst_hi=r["worst_hi"] and r["worst_hi"]["margin_hi_ps"], worst_hi_port=r["worst_hi"] and r["worst_hi"]["port"],
                    slot_read_fail=r["slot_read"]["fail"], guard_fail=r["guard"]["fail"],
                    start_skew_fail=f"{r['start_skew']['fail']}/{r['start_skew']['tree_ports']}",
                    ocv_max_lo=r.get("ocv_max_lo_ps"), ocv_max_hi=r.get("ocv_max_hi_ps"),
                    worst10=[{k: x.get(k) for k in ("port", "tag", "margin_lo_ps", "margin_hi_ps", "ocv_lo_ps", "ocv_hi_ps",
                                                    "source")} for x in w[:10]])
    res["corners"][c] = dict(cppr_lca=lca, landed_pairs=len(pairs["landed"]), no_ocv=summ(A),
                             with_ocv=summ(B) if B else dict(error=err))
    b = res["corners"][c]["with_ocv"]
    print(c, "lca", lca, "noOCV", A["verdict"], A["fail"], res["corners"][c]["no_ocv"]["worst_lo"],
          res["corners"][c]["no_ocv"]["worst_hi"], "| OCV", b.get("verdict"), "crossings", b.get("crossings"),
          "<100", b.get("below_need"), "worst lo/hi", b.get("worst_lo"), b.get("worst_hi"), "ocvmax", b.get("ocv_max_lo"),
          b.get("ocv_max_hi"), b.get("error", ""))
Path(a.out).write_text(json.dumps(res, indent=1))
