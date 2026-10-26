#!/usr/bin/env python3
"""HBM-LANDING/DCC+PRICE (10-18): price the d4g LANDINGS (lanes/LANDING-CONTRACT.md L4) on the HBM-PRICE5 d4g pricer.

Base = HBM-PRICE5 d4g_2ring_qbg (two rings + QBG, RTL1/2 ledger latencies; 1905.4 / 3258.7 / 946.2), i.e. the current
d4g price, whose per-class relay stage counts (results/arch/hbm_plan_study_1017/stages.json plan_b) charge N full-cycle
stations per traversal and NO landing.  The land plan (tools/hbm_die_v16/d4g_land_plan.py ->
results/arch/hbm_die_d4g/landing/land_plan_d4g.json, a MODEL pilot) gives, per class, the bits-weighted mean change of
a traversal over the class's links (links that stay intra-/neighbour-region change by 0):
    land_half  half-cycle stations + landing:  floor(N/2) + 1 + E   vs N   (delta_half_bw)   <- the adopted form
    land_full  full-cycle stations + landing:  N + 1 + E            vs N   (delta_full_bw)   (no-half-cycle reference)
The per-class stage count of plan_b is shifted by that delta (COLL_RING also moves the ring hop / XQ crossing cost:
knob xq = r_hop = COLL_RING).  Every other knob is the base's.

    PYTHONPATH=tools python3 -m hgi_sim.d4g_land_price_1018 --land-plan LP.json --out OUT.json
"""
from __future__ import annotations

import argparse
import copy
import datetime
import json
import multiprocessing as mp
from pathlib import Path

from hgi_sim import d4g_price5_1018 as P5     # patches d4g_quadrant_1017.d4g_added (PRICE5 base = 2 rings + QBG)
from hgi_sim import d4g_quadrant_1017 as Q
from hgi_sim import plan_study_price_1017 as PS
from hgi_sim import ds_mtp_verify as V

ROOT = Q.ROOT
CLK = Q.CLK


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stages", type=Path, default=ROOT / "results/arch/hbm_plan_study_1017/stages.json")
    ap.add_argument("--land-plan", type=Path, default=ROOT / "results/arch/hbm_die_d4g/landing/land_plan_d4g.json")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--jobs", type=int, default=12)
    a = ap.parse_args()
    lp = json.loads(a.land_plan.read_text())
    st0 = json.loads(a.stages.read_text())
    st0["plan_b_bd"] = Q.bd_stages(st0)
    led = Q.load_ledger()
    vb = PS.VARIANTS["b"]
    sts, knobs, deltas = {}, {}, {}
    for name, key in (("d4g_2ring_qbg", None), ("land_half", "delta_half_bw"), ("land_full", "delta_full_bw")):
        st = copy.deepcopy(st0)
        d = {}
        if key:
            for c, v in lp["per_class"].items():
                if c in st["plan_b"] and v.get(key):
                    d[c] = v[key]
                    st["plan_b"][c] = round(st["plan_b"][c] + v[key], 3)
            st["plan_b_bd"] = Q.bd_stages(st)
        sts[name] = st; deltas[name] = d
        knobs[name] = dict(Q.knob(Q.ADDERS, st, ledger=led), rings=2, ag_qbg=True)
    jobs = [("ds", f"{k}|{case}", case, vb, sts[k], knobs[k]) for k in sts for case in ("AR", "MTP_design", "draft_design")]
    jobs += [("qwen", f"{k}|qwen", vb, sts[k], knobs[k]) for k in sts]
    with mp.Pool(a.jobs) as pool:
        res = dict(pool.map(P5._any, jobs, chunksize=1))
    dref = json.loads((ROOT / "results/arch/hbm_mtp_1015/draft_rows/design.json").read_text())
    smt = dref["smallest_meeting_target"]["fixed"]
    mh_ctl = smt["step_cycles"] - smt["verify_cycles"] - smt["draft_cycles"] - smt["seed_cycles"]
    table = {}
    for k in sts:
        ar = res[f"{k}|AR"]["cycles"]
        d = res[f"{k}|draft_design"]
        step = res[f"{k}|MTP_design"]["cycles"] + d["draft_cycles"] + d["seed_cycles"] + mh_ctl
        table[k] = dict(ar_cycles=round(ar, 1), ar_tok_s=round(CLK / ar, 1), mtp_step_cycles=round(step, 1),
                        mtp_design_tok_s=round(V.TAU * CLK / step, 1), qwen_tok_s=res[f"{k}|qwen"]["tok_s"])
    b = table["d4g_2ring_qbg"]
    for t in table.values():
        for x, y in (("ar", "ar_tok_s"), ("mtp", "mtp_design_tok_s"), ("qwen", "qwen_tok_s")):
            t[f"d_{x}_pct_vs_d4g"] = round(100 * (t[y] / b[y] - 1), 2)
            if "land_full" in table:
                t[f"d_{x}_pct_vs_land_full"] = round(100 * (t[y] / table["land_full"][y] - 1), 2)
    out = dict(schema="opentallas.hbm_d4g_land_price.v1",
               generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               rule=__doc__, land_plan=str(a.land_plan), land_plan_status=lp.get("status"),
               stage_deltas=deltas, stages_plan_b={k: sts[k]["plan_b"] for k in sts}, table=table)
    print(json.dumps(dict(table=table, stage_deltas=deltas), indent=1))
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(out, indent=1, default=str) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
