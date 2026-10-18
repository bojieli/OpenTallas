#!/usr/bin/env python3
"""HBM-NET (owner question 10-16): per-crossing switch latency sensitivity of the HBM-accelerator arrays.

Re-runs hgi_sim.ds_die_split (same S2 schedule, same stages, same split transform) for the 96 x d4c (32 SM / 4 stacks,
TP-96) and 192 x d4f (16 SM / 2 stacks, TP-192, full core) arrays with the one-way switch crossing X in place of the
377.6 ns vendor budget (PHY/FEC 100 + Tomahawk-Ultra 250 + 2 x 3 m twinax 27.6).

CROSSING RULE (faithful to the base prices).  A collective record pays dX = X - 377.6 ns for each crossing that its
base price actually contains: k = 2 for ALL_REDUCE_SUM / GROUP_REDUCE_MCAST, 1 otherwise, and a record whose base
price is below k x 377.6 ns (a member of a merged collective train -- x_projections qa/kvraw/cmp/iwr, the seven
expert_intermediate gathers, the zero-cost engram / candidate-merge records) pays none: its crossing is paid by the
train's head.  ds_die_split's --extra-crossings rule (xc) instead charges every COLL record, which over-counts; the
'xc' rows reproduce it for comparison.  The MTP draft's collectives (ds_mtp_draft -> perf.coll_cycles, G 96) take X
through a patched perf.coll_cycles.  Qwen3-8B AR (TP-4 / TP-8) runs its all-reduces in package (perf.coll_cycles G <= 8,
no switch crossing), so it is invariant to X by construction.

    python3 -m hgi_sim.ds_switch_sens --stages ../results/arch/hbm_array_16sm_1016/stages.json --out OUT.json
"""
from __future__ import annotations

import argparse
import datetime
import json
import multiprocessing as mp
from pathlib import Path

from hgi_sim import ds_die_split as S
from hgi_sim import ds_mtp_verify as V
from hgi_sim import perf as P

CLK = S.CLK
CROSS0_NS = 377.6
_DX = {"dx": 0.0, "all": False}          # added cycles a crossing; all = the xc (every-record) convention
_SPLIT_CF = V.cost_fn                    # ds_die_split's wrapper (relay knob + split transform)


def kpaid(r, c0):
    k = 2 if r.op in ("ALL_REDUCE_SUM", "GROUP_REDUCE_MCAST") else 1
    if _DX["all"]:
        return k
    cr = CROSS0_NS * 1e-9 * CLK
    return k if c0 >= k * cr - 1 else (1 if c0 >= cr - 1 else 0)


def cost_fn(scale=None):
    base = _SPLIT_CF(scale)
    if not _DX["dx"]:
        return base
    pre = S._PREV_CF(scale)

    def cf(r, dyn, L):
        c, g, how = base(r, dyn, L)
        if r.unit == "COLL":
            c0 = pre(r, dyn, L)[0]
            c += kpaid(r, c0) * _DX["dx"]
        return c, g, how
    return cf


V.cost_fn = cost_fn
_COLL0 = P.coll_cycles


def _coll_patched(op, nbytes, G):
    c, g, how = _COLL0(op, nbytes, G)
    if G > 8:
        c += (2 if op in ("ALL_REDUCE_SUM", "GROUP_REDUCE_MCAST") else 1) * _DX["dx"]
    return c, g, how


VARIANTS = {
    "96x_d4c_32sm": dict(stages="d4c", split=dict(s=1, s_bw=1, G1=96, lanes=4, xc=0, m_owned=1.0), qwen=None),
    "192x_d4f_16sm": S.VARIANTS["d4f_16sm_tp192_full"],
}


def _job(job):
    name, case, var, stages, x_ns, allrec = job
    _DX["dx"] = (x_ns - CROSS0_NS) * 1e-9 * CLK
    _DX["all"] = allrec
    P.coll_cycles = _coll_patched if case == "draft_design" else _COLL0
    return name, S._job((name, case, var, stages))[1]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stages", type=Path, required=True)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--jobs", type=int, default=16)
    ap.add_argument("--x", default="377.6,500,650,800,1132.8")
    a = ap.parse_args()
    stages = json.loads(a.stages.read_text())
    xs = [float(v) for v in a.x.split(",")]
    jobs = []
    for vk, var in VARIANTS.items():
        for x in xs:
            for case in ("AR", "MTP_design", "draft_design"):
                jobs.append((f"{vk}|{x}|{case}", case, var, stages, x, False))
        for case in ("AR", "MTP_design", "draft_design"):      # the ds_die_split xc=2 convention (2-tier, every record)
            jobs.append((f"{vk}|xc2|{case}", case, var, stages, 3 * CROSS0_NS, True))
    with mp.Pool(a.jobs) as pool:
        res = dict(pool.map(_job, jobs, chunksize=1))
    dref = json.loads((S.ROOT / "results/arch/hbm_mtp_1015/draft_rows/design.json").read_text())
    smt = dref["smallest_meeting_target"]["fixed"]
    mh_ctl = smt["step_cycles"] - smt["verify_cycles"] - smt["draft_cycles"] - smt["seed_cycles"]
    table = {}
    for vk in VARIANTS:
        for x in [str(v) for v in xs] + ["xc2"]:
            k = f"{vk}|{x}"
            ar = res[f"{k}|AR"]["cycles"]
            d = res[f"{k}|draft_design"]
            st = res[f"{k}|MTP_design"]["cycles"] + d["draft_cycles"] + d["seed_cycles"] + mh_ctl
            table[k] = dict(x_ns=x, ar_cycles=round(ar, 1), ar_tok_s=round(CLK / ar, 1), mtp_step_cycles=round(st, 1),
                            mtp_design_tok_s=round(V.TAU * CLK / st, 1), draft_cycles=d["draft_cycles"])
    for k, t in table.items():
        vk = k.split("|")[0]
        b = table[f"{vk}|{xs[0]}"]
        r96 = table[f"96x_d4c_32sm|{t['x_ns']}"] if f"96x_d4c_32sm|{t['x_ns']}" in table else None
        t["ar_vs_own_baseline_pct"] = round(100 * (t["ar_tok_s"] / b["ar_tok_s"] - 1), 2)
        t["mtp_vs_own_baseline_pct"] = round(100 * (t["mtp_design_tok_s"] / b["mtp_design_tok_s"] - 1), 2)
        if r96:
            t["ar_vs_96x_same_x_pct"] = round(100 * (t["ar_tok_s"] / r96["ar_tok_s"] - 1), 2)
            t["mtp_vs_96x_same_x_pct"] = round(100 * (t["mtp_design_tok_s"] / r96["mtp_design_tok_s"] - 1), 2)
    print(json.dumps(table, indent=1))
    if a.out:
        a.out.write_text(json.dumps(dict(
            schema="opentallas.hbm_switch_sensitivity_1016.v1",
            generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            rule=__doc__, variants=VARIANTS, stages_source=str(a.stages), table=table,
            runs={k: {x: y for x, y in v.items() if x != "records"} for k, v in res.items()}),
            indent=1, default=float) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
