#!/usr/bin/env python3
"""HBM-P6-CMP (10-23): price the HBM over-cap LEAF-SPLIT latency shifts on the plan price of record.

Same machinery and CLI as hgi_sim.plan_study_price_1017 (the pricer physical/die_plan/hbm/price_p5.sh runs); this module
only wraps the record cost function (the d4g_quadrant_1017 / ds_switch_sens hook pattern) with the per-record exposure
of the leaf-split shifts of tools/hbm_static/leaf_split_latency.py, when that table is enabled (OT_HBM_LEAF_SPLIT=1).
With it off the price is byte-identical to plan_study_price_1017.

Per-record rule (every record of the static schedule pays the shift of its unit once: the twin's results arrive that
many edges later and the next dependent record starts after them; serial-domain edges (SU / SFU / HC core, 0.9 GHz)
are converted to 1.2 GHz stream cycles x 4/3, COLL / TKM edges are stream edges):
  SFU-using record (SFU, or SU with an SFU leg; d4g_quadrant_1017.sfu_using)  sfu_op_horizon 3 serial  -> +4.00
  SU-executed record (d4g_quadrant_1017.su_exec)                              su_write 4 serial        -> +5.33
  HC.HC_MIX / HC.HC_MIX_POST (Sinkhorn tail result)                           hc_tail_result 7 serial  -> +9.33
  COLL reduce records (ALL_REDUCE / REDUCE_SCATTER / GROUP_REDUCE_MCAST)      coll_reduce_pub 1 stream -> +1
  COLL.TOPK_MERGE                                                             tkm_done 2 stream        -> +2

    OT_HBM_LEAF_SPLIT=1 PYTHONPATH=tools python3 -m hgi_sim.leaf_split_price_1023 --stages S.json --x-c 377.6 --out O.json
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

from hgi_sim import plan_study_price_1017 as PS
from hgi_sim import d4g_quadrant_1017 as Q
from hgi_sim import ds_mtp_verify as V
from hgi_sim import ds_die_split as S

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hbm_static"))
import leaf_split_latency as LS  # noqa: E402

SERIAL = 4.0 / 3.0
RED_OPS = ("ALL_REDUCE", "REDUCE_SCATTER", "GROUP_REDUCE_MCAST")


def added(r):
    """(stream cycles, rule) of the leaf-split shifts on one record (0 when the table is off)."""
    if not LS.enabled():
        return 0.0, None
    op = getattr(r, "orig_op", f"{r.unit}.{r.op}")
    add, why = 0.0, []
    if Q.sfu_using(r):
        add += LS.shift("sfu_op_horizon") * SERIAL; why.append("sfu")
    if Q.su_exec(r):
        add += LS.shift("su_write") * SERIAL; why.append("su")
    if op in ("HC.HC_MIX", "HC.HC_MIX_POST"):
        add += LS.shift("hc_tail_result") * SERIAL; why.append("hc")
    if r.unit == "COLL" and r.op in RED_OPS:
        add += LS.shift("coll_reduce_pub"); why.append("coll_red")
    if op == "COLL.TOPK_MERGE":
        add += LS.shift("tkm_done"); why.append("tkm")
    return add, "+".join(why) or None


HITS = Counter()
_PREV = V.cost_fn


def cost_fn(scale=None):
    base = _PREV(scale)

    def cf(r, dyn, L):
        c, g, how = base(r, dyn, L)
        a, why = added(r)
        if why:
            HITS[why] += 1
        return c + a, g, how
    return cf


V.cost_fn = cost_fn

# Qwen3-8B AR (ds_die_split._qwen_job) builds its own record cost on timing.cost and calls T.schedule directly: wrap the
# cost_fn that job hands to T.schedule (one job at a time a pool worker, restored after).
_QJ = S._qwen_job


def _qwen_job(job):
    orig = S.T.schedule

    def sched(recs, *args, cost_fn=None, **kw):
        def cf(r, dyn, L):
            c, g, how = cost_fn(r, dyn, L)
            a, why = added(r)
            return c + a, g, how
        return orig(recs, *args, cost_fn=cf, **kw)
    S.T.schedule = sched
    try:
        return _QJ(job)
    finally:
        S.T.schedule = orig


S._qwen_job = _qwen_job

if __name__ == "__main__":
    print(f"LEAF_SPLIT enabled={LS.enabled()} table={ {k: v[0] for k, v in LS.SHIFTS.items()} }", file=sys.stderr)
    raise SystemExit(PS.main())
