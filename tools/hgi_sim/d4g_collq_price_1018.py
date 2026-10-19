#!/usr/bin/env python3
"""HBM-COLLQ (10-18): re-price DS AR / MTP and Qwen on the adopted d4g (two rings + QBG) with the MEASURED per-quadrant
COLL gather master (rtl ot_hgi_coll_gq; bench tb_hgi_coll_gq PASS) instead of the ring-schedule model:

  ag_collq   every C1 all-gather costs the gather-master span: launch -> fire 3 + fire -> last bank write
             1 + 3 ((K-1) >> 1) + ((K-1) & 1) + 38, K = ceil(F / rings), + 3 x COLL_RING die relay stages
             (DS R2 shapes: expert-intermediate plain 91 / QBG 52, o-group 61 / 45, engram 181 / 75 edges fire -> write;
             results/arch/hbm_die_d4g/collq/collq_schedule.json).  Cut-through as before: only the issue part may
             overlap the off-die delivery stream D; the compiler keeps min(AG, 3 D multicast).
  ra_extra   +2 edges on every non-gather COLL record (every ISA ring-A command and rc_d passes the master's ring-A
             merge register: all ring-A-relative compiler constants +2).

Variants (all on hgi_sim.d4g_quadrant_1017 + the HBM-B-RTL3 latency ledger; d4g_2ring_qbg reproduces price.json):
  b_plan, d4g_2ring_qbg (reference), collq_spans (ag_collq only), collq_ra2 (ra_extra only), collq (both = the
  as-built d4g COLL), and the *_upper bounds (no cut-through, no multicast, broadcast-depth stages).

    PYTHONPATH=tools python3 -m hgi_sim.d4g_collq_price_1018 --out results/arch/hbm_d4g_price_1017/collq/price_collq.json
"""
from __future__ import annotations

import argparse
import datetime
import json
import multiprocessing as mp
import re
from pathlib import Path

from hgi_sim import d4g_quadrant_1017 as Q
from hgi_sim import plan_study_price_1017 as PS
from hgi_sim import ds_die_split as S
from hgi_sim import ds_relay_latency as RL
from hgi_sim import ds_mtp_verify as V

ROOT = Q.ROOT
CLK = Q.CLK


def ag_census(kn):
    """per C1 tag (AR programme, plan b): F a quadrant, old ring-model AG vs measured gather-master span"""
    S.set_variant(PS.VARIANTS["b"], json.loads((ROOT / "results/arch/hbm_plan_study_1017/stages.json").read_text()))
    prog = RL.compile_case("AR")
    rows = {}
    for r in prog:
        if Q.classify(r) != "C1":
            continue
        B, wire = Q.coll_bytes(r)
        qbg = Q.qbg_ok(r)
        if qbg:
            B = B // Q.VM_WORD_B + B // Q.VM_WORD_B // Q.QBG_BLOCK
        f1 = max(1, -(-wire // kn["G1"] // 64))
        D = S.deliver(f1, kn["G1"], kn["lanes"])
        F = -(-B // Q.NQ // Q.RING_FLIT_B)
        ser, fixed = Q.collq_span(F, 2)
        old, _ = Q.ag_cycles(B, kn["r_hop"], D, True, 2)
        new = max(0.0, ser - D) + fixed + 3 * kn["r_hop"]
        k = re.sub(r"\s.*", "", r.tag or "")
        e = rows.setdefault(k, dict(records=0, qbg=qbg, F=F, span_fire_to_write=ser + fixed - Q.COLLQ_FIRE_FROM_LAUNCH,
                                    D=round(D, 1), old_ring_model=round(min(old, 3 * D), 1),
                                    measured=round(min(new, 3 * D), 1)))
        e["records"] += 1
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stages", type=Path, default=ROOT / "results/arch/hbm_plan_study_1017/stages.json")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--jobs", type=int, default=24)
    a = ap.parse_args()
    st = json.loads(a.stages.read_text())
    st["plan_b_bd"] = Q.bd_stages(st)
    led = Q.load_ledger()
    vb = PS.VARIANTS["b"]
    vbd = dict(vb, stages="plan_b_bd")
    A = Q.ADDERS
    nom = lambda **x: (vb, dict(Q.knob(A, st, ledger=led), rings=2, ag_qbg=True, **x))
    upp = lambda **x: (vbd, dict(Q.knob([y for y in A if y != "BD"], st, nominal=False, ledger=led),
                                 allow_mcast=False, rings=2, ag_qbg=True, **x))
    variants = {"b_plan": (vb, None),
                "d4g_2ring_qbg": nom(),
                "collq_spans": nom(ag_collq=True),
                "collq_ra2": nom(ra_extra=Q.COLLQ_RA_EXTRA),
                "collq": nom(ag_collq=True, ra_extra=Q.COLLQ_RA_EXTRA),
                "d4g_2ring_qbg_upper": upp(),
                "collq_upper": upp(ag_collq=True, ra_extra=Q.COLLQ_RA_EXTRA)}
    jobs = [("ds", f"{k}|{case}", case, v, st, kn) for k, (v, kn) in variants.items()
            for case in ("AR", "MTP_design", "draft_design")]
    jobs += [("qwen", f"{k}|qwen", v, st, kn) for k, (v, kn) in variants.items()]
    with mp.Pool(a.jobs) as pool:
        cen = pool.apply_async(ag_census, (variants["collq"][1],))
        res = dict(pool.map(Q._any, jobs, chunksize=1))
        census = cen.get()
    dref = json.loads((ROOT / "results/arch/hbm_mtp_1015/draft_rows/design.json").read_text())
    smt = dref["smallest_meeting_target"]["fixed"]
    mh_ctl = smt["step_cycles"] - smt["verify_cycles"] - smt["draft_cycles"] - smt["seed_cycles"]
    table = {}
    for k in variants:
        ar = res[f"{k}|AR"]["cycles"]
        d = res[f"{k}|draft_design"]
        step = res[f"{k}|MTP_design"]["cycles"] + d["draft_cycles"] + d["seed_cycles"] + mh_ctl
        table[k] = dict(ar_cycles=round(ar, 1), ar_tok_s=round(CLK / ar, 1), mtp_step_cycles=round(step, 1),
                        mtp_design_tok_s=round(V.TAU * CLK / step, 1), qwen_tok_s=res[f"{k}|qwen"]["tok_s"])
    b, g = table["b_plan"], table["d4g_2ring_qbg"]
    for t in table.values():
        for key, col in (("ar", "ar_tok_s"), ("mtp", "mtp_design_tok_s"), ("qwen", "qwen_tok_s")):
            t[f"d_{key}_pct_vs_b_plan"] = round(100 * (t[col] / b[col] - 1), 2)
            t[f"d_{key}_pct_vs_d4g_model"] = round(100 * (t[col] / g[col] - 1), 2)
    out = dict(schema="opentallas.hbm_d4g_price_collq.v1",
               generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               rule=__doc__, ledger=led, ag_census_AR=census, table=table,
               earlier_estimate=dict(d4g_2ring_qbg_ar_pct=-3.69, mtp_pct=-3.32, qwen_pct=-0.94,
                                     source="results/arch/hbm_d4g_price_1017/price.json (HBM-PRICE5, ring-schedule model)"))
    print(json.dumps(dict(table=table, ag_census_AR=census), indent=1, default=str))
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(out, indent=1, default=str) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
