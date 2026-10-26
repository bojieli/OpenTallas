#!/usr/bin/env python3
"""H-PLANSTUDY (10-17): token rate of the three HBM die plans on the existing array price model.

Same machinery as hgi_sim.ds_die_split / ds_switch_sens (HBM-NET 10-16): the native DS programme (AR token, the MTP
3,500 design point: verify P = 6 + the compiled R-row draft + main-hidden stores + control) and the Qwen3-8B AR
programme keep their base prices; added on top are (1) the per-class relay-stage change of the die plan
(ds_relay_latency crossing rule, v5carry -> the plan's v6_eval per-class stages, absolute-leg SM rule) and (2) the
split transform for the SM count per die (s = 32 / SMs, G1 = 96 s), and (3) the switch crossing X (ds_switch_sens
kpaid rule: a collective pays dX only for the crossings its base price contains).

Variants:
  a       d4f as is      16 SM, TP-192, 4 COLL delivery lanes, stages = plan_a (v6_eval re-run of d4f_a2p_fullcore)
  b       per-quadrant   16 SM, TP-192, 4 lanes, stages = plan_b_inner
  c_L2    8-SM die       TP-384 (s = 4, G1 = 384), 2 COLL engines = 2 delivery lanes, stages = plan_c_inner
  c_L4    8-SM die with 2 delivery lanes per COLL engine (4 a die)
  X       377.6 ns (one tier, 200G or 100G ports, all copper) and the (c) fabric cases from array_net_1017.json
Qwen3-8B: a / b TP-8 (G 8, in package, as ds_die_split); c TP-16 (G 16 > 8: one switch crossing an all-reduce
phase, xc = 1) and c TP-8 on 8-SM dies (rows per SM x 2, no crossing).

    python3 -m hgi_sim.plan_study_price_1017 --stages STAGES.json --x-c 377.6,428.8,480,1132.8 --out OUT.json
"""
from __future__ import annotations

import argparse
import datetime
import json
import multiprocessing as mp
from pathlib import Path

from hgi_sim import ds_switch_sens as W
from hgi_sim import ds_die_split as S
from hgi_sim import ds_mtp_verify as V

CLK = S.CLK
VARIANTS = {
    "a": dict(stages="plan_a", split=dict(s=2, s_bw=2, G1=192, lanes=4, xc=0, m_owned=0.6),
              qwen=dict(sm_s=1, bw_s=2, G0=4, G1=8, lanes=4)),
    "b": dict(stages="plan_b", split=dict(s=2, s_bw=2, G1=192, lanes=4, xc=0, m_owned=0.6),
              qwen=dict(sm_s=1, bw_s=2, G0=4, G1=8, lanes=4)),
    "c_L2": dict(stages="plan_c", split=dict(s=4, s_bw=4, G1=384, lanes=2, xc=0, m_owned=0.6),
                 qwen=dict(sm_s=1, bw_s=4, G0=4, G1=16, lanes=2, xc=1)),
    "c_L4": dict(stages="plan_c", split=dict(s=4, s_bw=4, G1=384, lanes=4, xc=0, m_owned=0.6),
                 qwen=dict(sm_s=1, bw_s=4, G0=4, G1=16, lanes=4, xc=1)),
}
QWEN_EXTRA = {"c_qwen_tp8": dict(stages="plan_c", split=None, qwen=dict(sm_s=2, bw_s=4, G0=4, G1=8, lanes=2)),
              "c_qwen_tp16_noX": dict(stages="plan_c", split=None, qwen=dict(sm_s=1, bw_s=4, G0=4, G1=16, lanes=2, xc=0))}


def _q(job):
    name, var, stages = job
    return S._qwen_job((name, var, stages))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stages", type=Path, required=True)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--jobs", type=int, default=16)
    ap.add_argument("--x-c", default="377.6,428.8,480,1132.8")
    a = ap.parse_args()
    stages = json.loads(a.stages.read_text())
    xc = [float(v) for v in a.x_c.split(",")]
    jobs = []
    for vk, var in VARIANTS.items():
        xs = xc if vk.startswith("c") else [377.6]
        for x in xs:
            for case in ("AR", "MTP_design", "draft_design"):
                jobs.append((f"{vk}|{x}|{case}", case, var, stages, x, False))
    qjobs = [(f"{vk}|qwen", var, stages) for vk, var in list(VARIANTS.items()) + list(QWEN_EXTRA.items())]
    with mp.Pool(a.jobs) as pool:
        qr = pool.map_async(_q, qjobs, chunksize=1)
        res = dict(pool.map(W._job, jobs, chunksize=1))
        res.update(dict(qr.get()))
    dref = json.loads((S.ROOT / "results/arch/hbm_mtp_1015/draft_rows/design.json").read_text())
    smt = dref["smallest_meeting_target"]["fixed"]
    mh_ctl = smt["step_cycles"] - smt["verify_cycles"] - smt["draft_cycles"] - smt["seed_cycles"]
    table = {}
    for vk in VARIANTS:
        xs = xc if vk.startswith("c") else [377.6]
        for x in xs:
            k = f"{vk}|{x}"
            ar = res[f"{k}|AR"]["cycles"]
            d = res[f"{k}|draft_design"]
            st = res[f"{k}|MTP_design"]["cycles"] + d["draft_cycles"] + d["seed_cycles"] + mh_ctl
            table[k] = dict(x_ns=x, ar_cycles=round(ar, 1), ar_tok_s=round(CLK / ar, 1), mtp_step_cycles=round(st, 1),
                            mtp_design_tok_s=round(V.TAU * CLK / st, 1))
    qwen = {k.split("|")[0]: v for k, v in res.items() if k.endswith("|qwen")}
    out = dict(schema="opentallas.hbm_plan_study_1017.price.v1",
               generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               rule=__doc__, variants=VARIANTS, qwen_extra=QWEN_EXTRA, stages=stages, table=table, qwen=qwen,
               runs={k: {x: y for x, y in v.items() if x not in ("records", "unit_busy")} for k, v in res.items()})
    print(json.dumps(dict(table=table, qwen=qwen), indent=1))
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(out, indent=1, default=float) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
