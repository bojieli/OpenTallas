#!/usr/bin/env python3
"""HH-5 (10-18, coordinator 0ix (5)): re-price the adopted d4g token (two rings + QBG, every d4g adder, RTL ledger) with
the HBM SU reducer ingress AS BUILT, on the HBM-B-RTL3 d4g pricer (hgi_sim.d4g_quadrant_1017).

ORIGIN (LB2-HBM-CDS 10-18, claude/lb2-hbm-cds-1018 @1b82239d6, tools/hbm_layer_vehicle/layer_images.py reducer_bound):
  each SU quarter's ot_hbm_su_reduce_static takes ONE external operand per edge: red_sel = {v, op3, osel, lane7} picks one
  lane of the quarter's 128 (ot_hbm_su_static_pgslice.sv:355-361 slice_x -> ot_hbm_su_static_qcore_r5.sv rc_x =
  slice_x[e_sl]); a lane's ro_v/ro_x is live one edge; dependent reducer ops issue >= DEP 10 edges apart, commits /
  exports +LAT 9 (ot_hbm_su_reduce_static.sv:1-8).  The die has 4 quarters (su_<q><g>: 4 x 4 pgslices of 32 lanes) ->
  4 reducers.  The price model charged SU reductions with the ROM SU layout model (timing.su_cost: nv + depth dR at
  su_lanes 1024), i.e. a full-width reduction ingress; CDS bounds: q_norm.ss 428 vs 137 priced, engram.ss* 5268 vs 173.

RE-PRICE (knob `su_red` on the d4g knob, applied to every SU.VOP with sut.red, also inside the MTP rows-x-P records):
  words      = n x m of operand A (the reduced lane values of the record on one die)
  bound      = layer_images.reducer_bound(words) (CDS rule, verbatim): ingress ceil(words / 4) + chunk tail
               DEP (1 + tree_q) + LAT + quarter-join DEP 2 + LAT
  local      = bound - (2 DEP + LAT)  (the 4-quarter join is ALREADY priced by the XQT adder su_tree = 28 measured
               RF_TREE_UP/DN + XQ crossings; not counted twice)
  unit cost  = max(model cost, local + SU.issue_overhead + HBM first access if any)
  The ingress rate is achievable with the RTL as built (the compiler re-issues the issue group so the selected lane's
  ro_x is live on its edge; 127 of 128 lane results per edge are discarded), so this is the as-built price, a lower
  bound only in that RF relay / class-4 read edges are not added.  Numerics unchanged (golden csum8 + pairwise tree on
  reducer ops 0/1/2/4).
  su_red_w<W> (sizing): the same with W reducer operands accepted per edge per quarter (a widened ingress).
  su_red_rows (info): the same bound with the chunk tree of ONE row (m independent rows) -- tail 30 edges smaller.

    PYTHONPATH=tools python3 -m hgi_sim.d4g_su_red_1018 --jobs 40 --widths 2,4,8,16,32 \
        --out results/arch/hbm_d4g_price_1017/su_red/price_su_red_w.json
    (run 10-18 on ot-epyc5, bundle /srv/opentallas-scratch/claude/hh5-sured/src = the HBM-PRICE5 bundle + tools/hgi_sim
    of claude/hh5-su-reducer-1018; the d4g base reproduces HBM-PRICE5 d4g_2ring_qbg 1905.4 / 3258.7 / 946.2 exactly)

RESULT (vs d4g_2ring_qbg): as built DS AR 1905.4 -> 1796.6 (-5.71%), DS MTP 3258.7 -> 2685.7 (-17.58%), Qwen 946.2 ->
494.3 (-47.76%; Qwen softmax max / exp_sum over 8 heads x 8192 ctx = 65,536 words: 302 / 524 -> 16,517 cycles each).
Over the 5% accepted-cost limit -> WIDEN.  Sizing: W 8 -0.38 / -1.57 / -9.12; W 16 -0.14 / -0.59 / -4.05;
W 32 -0.04 / -0.19 / -1.30 (AR / MTP / Qwen %).
"""
from __future__ import annotations

import argparse
import datetime
import json
import multiprocessing as mp
from collections import defaultdict
from pathlib import Path

from hgi_sim import d4g_quadrant_1017 as Q
from hgi_sim import plan_study_price_1017 as PS
from hgi_sim import ds_die_split as S
from hgi_sim import ds_relay_latency as RL
from hgi_sim import ds_mtp_verify as V
from hgi_sim import timing as T

CLK = Q.CLK
ROOT = Q.ROOT
RED_DEP, RED_LAT, RED_QUARTERS = 10, 9, 4          # ot_hbm_su_reduce_static.sv:1-8; 4 quarters a die
JOIN = 2 * RED_DEP + RED_LAT                        # 4-quarter join + final export (priced by XQT su_tree)

_MODE = {"m": None, "w": 1}                         # m: None | "cds" | "rows"; w: ingress width (per job; fork pool)
_ORIG_SU = T.su_cost


def reducer_bound(words, row_words=None, width=1):
    """CDS 10-18 rule (tools/hbm_layer_vehicle/layer_images.py reducer_bound), optional per-row chunk tree;
    width = reducer operands accepted per edge per quarter (1 as built; >1 = a widened ingress, priced for sizing)"""
    per_q = -(-words // (RED_QUARTERS * width))
    per_q_tree = -(-(words if row_words is None else row_words) // RED_QUARTERS)
    chunks_q = max(1, -(-per_q_tree // 8))
    tree_q = (chunks_q - 1).bit_length()
    tail = RED_DEP * (1 + tree_q) + RED_LAT + JOIN
    return per_q + tail


# HH-6 (10-18/19): the built widening = per-pgslice csum8 pre-tree (ot_hbm_su_red_pretree_s, 4 per quarter) + quarter
# join (ot_hbm_su_red_pretree_j in qcore_r5): the 128 lanes of a quarter enter in ONE edge (lockstep SIMD lanes emit one
# issue block per edge), the 128-word aligned csum8 subtree reaches the reducer PT edges later as ONE operand; the
# reducer then does the pairwise tree over block subtrees (LOAD/ADD_EXT per arriving block + ADD_TREE above the pairs).
# A row shorter than 128 occupies one block (masked +0 / invalid lanes; no row packing priced).
PT_EDGES = 70          # measured by the pretree bench (tb_hbm_su_red_pretree: tree_cmd edge E -> tree_x at qcore rc_x)
PT_BLOCK = 128


def pretree_bound(n, m):
    blocks = m * -(-n // PT_BLOCK)
    bq = -(-blocks // RED_QUARTERS)
    pairs = -(-bq // 2)
    ops = bq + max(0, pairs - 1)                    # arrivals (LOAD / ADD_EXT) + ADD_TREE above the first pair level
    depth = (pairs - 1).bit_length()
    return PT_EDGES + ops + RED_DEP * (1 + depth) + RED_LAT + JOIN


def red_words(r, dyn, L):
    _, n, m, _, _ = T.eff(r.desc["A"], dyn, L)
    return int(n), int(m or 1)


def su_cost(r, dyn, L):
    c, how = _ORIG_SU(r, dyn, L)
    mode = _MODE["m"]
    sut = getattr(r, "sut", None)
    if not mode or not (isinstance(sut, dict) and sut.get("red")):
        return c, how
    n, m = red_words(r, dyn, L)
    if mode == "pretree":
        b = pretree_bound(n, m) - JOIN
    else:
        b = reducer_bound(n * m, n if mode == "rows" else None, _MODE["w"]) - JOIN
    hbm = any(d.space == "HBM" for d in r.desc.values())
    floor = b + T.cv("units", "SU.issue_overhead") + (T.first_access() if hbm else 0.0)
    if floor > c:
        return floor, how + f"; SU reducer ingress as built: {n * m} w -> {b} edges (1 operand/edge/quarter)"
    return c, how


T.su_cost = su_cost


def _any(job):
    kn = job[-1]
    _MODE["m"] = (kn or {}).get("su_red")
    _MODE["w"] = (kn or {}).get("su_red_w", 1)
    return Q._any(job)


def census(mode):
    """AR / MTP_design programmes (plan b stages): every SU reduction record, model vs as-built unit cycles"""
    S.set_variant(PS.VARIANTS["b"], json.loads((ROOT / "results/arch/hbm_plan_study_1017/stages.json").read_text()))
    out = {}
    for case in ("AR",):
        prog = RL.compile_case(case)
        agg = defaultdict(lambda: dict(n=0, model=0.0, as_built=0.0))
        dyn = T.Dyn(V.DT.POS)
        for r in prog:
            sut = getattr(r, "sut", None)
            if not (r.unit == "SU" and isinstance(sut, dict) and sut.get("red")):
                continue
            L = getattr(r, "layer", 0) if isinstance(getattr(r, "layer", 0), int) else 0
            try:
                _MODE["m"] = None
                c0 = _ORIG_SU(r, dyn, L)[0]
                _MODE["m"] = mode
                c1 = su_cost(r, dyn, L)[0]
                n, m = red_words(r, dyn, L)
            except Exception as ex:                      # dyn-dependent descriptor: report, do not guess
                agg[r.tag]["error"] = repr(ex)
                continue
            a = agg[r.tag]
            a.update(words=n * m, n=a["n"] + 1)
            a["model"] += c0
            a["as_built"] += c1
        out[case] = {k: dict(v, model=round(v["model"], 1), as_built=round(v["as_built"], 1)) for k, v in agg.items()}
    _MODE["m"] = None
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stages", type=Path, default=ROOT / "results/arch/hbm_plan_study_1017/stages.json")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--jobs", type=int, default=24)
    ap.add_argument("--only", default="", help="comma list of variant names to price (default all)")
    ap.add_argument("--widths", type=lambda x: [int(v) for v in x.split(",") if v], default=[],
                    help="also price a widened reducer ingress of W operands/edge/quarter (sizing), e.g. 2,4,8,16")
    a = ap.parse_args()
    st = json.loads(a.stages.read_text())
    st["plan_b_bd"] = Q.bd_stages(st)
    led = Q.load_ledger()
    vb = PS.VARIANTS["b"]
    vbd = dict(vb, stages="plan_b_bd")
    base = dict(Q.knob(Q.ADDERS, st, ledger=led), rings=2, ag_qbg=True)
    upper = dict(Q.knob([x for x in Q.ADDERS if x != "BD"], st, nominal=False, ledger=led), allow_mcast=False,
                 rings=2, ag_qbg=True)
    variants = {"b_plan": (vb, None),
                "d4g_2ring_qbg": (vb, base),
                "d4g_2ring_qbg_su_red": (vb, dict(base, su_red="cds")),
                "d4g_2ring_qbg_su_red_rows_info": (vb, dict(base, su_red="rows")),
                **{f"d4g_2ring_qbg_su_red_w{w}": (vb, dict(base, su_red="cds", su_red_w=w)) for w in a.widths},
                "d4g_2ring_qbg_su_pretree": (vb, dict(base, su_red="pretree")),
                "d4g_2ring_qbg_upper": (vbd, upper),
                "d4g_2ring_qbg_upper_su_red": (vbd, dict(upper, su_red="cds"))}
    if a.only:
        keep = set(a.only.split(",")) | {"b_plan", "d4g_2ring_qbg", "d4g_2ring_qbg_upper", "d4g_2ring_qbg_upper_su_red"}
        variants = {k: v for k, v in variants.items() if k in keep}
    jobs = [("ds", f"{k}|{case}", case, v, st, kn) for k, (v, kn) in variants.items()
            for case in ("AR", "MTP_design", "draft_design")]
    jobs += [("qwen", f"{k}|qwen", v, st, kn) for k, (v, kn) in variants.items()]
    with mp.Pool(a.jobs) as pool:
        cen = pool.apply_async(census, ("pretree" if a.only else "cds",))
        res = dict(pool.map(_any, jobs, chunksize=1))
        cens = cen.get()
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
    for ref in ("b_plan", "d4g_2ring_qbg"):
        r0 = table[ref]
        for t in table.values():
            for x, y in (("ar", "ar_tok_s"), ("mtp", "mtp_design_tok_s"), ("qwen", "qwen_tok_s")):
                t[f"d_{x}_pct_vs_{ref}"] = round(100 * (t[y] / r0[y] - 1), 2)
    u0, u1 = table["d4g_2ring_qbg_upper"], table["d4g_2ring_qbg_upper_su_red"]
    for x, y in (("ar", "ar_tok_s"), ("mtp", "mtp_design_tok_s"), ("qwen", "qwen_tok_s")):
        u1[f"d_{x}_pct_vs_d4g_2ring_qbg_upper"] = round(100 * (u1[y] / u0[y] - 1), 2)
    out = dict(schema="opentallas.hbm_d4g_su_red_1018.v1",
               generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               rule=__doc__, table=table, su_reduction_census=cens, ledger=led)
    print(json.dumps(dict(table=table, census=cens), indent=1, default=str))
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(out, indent=1, default=str) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
