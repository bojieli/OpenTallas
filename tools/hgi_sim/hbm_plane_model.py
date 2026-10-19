#!/usr/bin/env python3
"""HBM-MTP / MTP-MODEL (10-18): compiler timing model of the NEXT HBM die variant with P position lanes, on the CURRENT
d4g price basis (plan (b) d4g = HBM-PRICE5 `d4g_2ring_qbg`: two rings + QBG, RTL1/2 ledger latencies; the price of
record DS AR 1,905.4 / DS MTP design 3,258.7 / Qwen AR 946.2 tok/s).  Design study OUTSIDE the release closure.

A P-lane die is the d4g die with (owner outline, lanes/HBM-MTP.md):
 (1) one parameter P (accumulator lanes per SM MAC column, query lanes per SM attention engine);
 (2) SM.MATVEC: each HBM weight word is broadcast to P accumulator lanes (P x MAC; HBM BW, SRAM, VM ports and PHY
     unchanged).  A record of N rows costs the AR record when N <= P (weight-stream-bound) and ceil(N / P) x the line
     time otherwise, never faster than the per-SM HBM share (ds_mtp_verify sm_mode "slots", sm_k = P:
     c = c_AR x max(1, ceil(N / P) / 1.374), 1.374 = 136 B line / 98.96 B/cycle/SM, owner 10-12);
 (3) every ISA record carries a row count N: cost = c1 + (N - 1) II (setup + pipelined rows) for FUSED (HC pre-norm /
     post / QDQ), HC mix + Sinkhorn, SU (+ SFU), COLL (gathers / merges: payload x N, fixed latency once; shared
     all-gathers / reduce-mcasts carry N x the bytes), IDX (index: P queries over one key stream; top-k: heap row reset),
     DMA (first access once), ARGMAX.  II per family = ds_mtp_verify.row_ii; FUSED.HC_PRE_NORM uses the MEASURED
     P6 RTL II 197 (results/arch/hbm_mtp_1015/p6_rtl_2330: 1,451 cycles for 6 rows vs 466 for one); every other II is
     PRICED from the unit's table / structure (labelled in summary.json `row_ii`);
 (4) KV-line-stationary multi-query attention (option B, attention on the SM engines, measured component spans
     b_measured_model.json): each KV line is streamed once and applied to every lane whose sparse top-k mask selects it:
     a record of N query rows costs fixed + comp x U(N) / U(1) per pass (fixed = first access + dispatch + publish +
     cross-SM merge, comp = the measured component span incl. the line stream), U = |union of selected lines|:
     window 128 + N - 1 (exact, consecutive positions) + the compressed top-512 union (T 640 records);
     the top-512 overlap of consecutive positions is UNMEASURED (MTP-STATS: no indexer capture): HEADLINE at the upper
     bound N x 512 (MTP-STATS recommendation), the full-overlap lower bound 512 as a bracket; independent users:
     U = N x U(1) exactly; the compiler takes min over pass counts k >= ceil(N / P);
 (5) MoE expert union: the verify reads the union U_e of the N positions' top-6 (weight streams ~ U_e), grouped GEMM
     per expert over the lanes routed to it (P_e = 6 N / U_e rows a slot, ceil(P_e / P) passes); U_e from MTP-STATS
     (DSpark verify decorrelated estimate, P = 6: mean 24.66 / p90 30 / max 36; independent users: mixed workloads);
 (6) DSpark draft on the same die: the R = 5 block rows compiled as R-row records under the same P-lane configuration
     (ds_mtp_draft.draft_step), Markov / demb serial; OVERLAP: the SEED of the next draft (main_proj / wkv over the
     6 verify columns' hidden) depends only on the verify's last-layer hidden, so it is scheduled JOINTLY with the
     verify's head segment (final norm, LM head, argmax / merge) on the S2 command-processor schedule (shared SM / HBM /
     COLL / SU resources, in-order dispatch, both orders tried: the compiler's choice); credit = head + seed - joint.
     Everything after the accept (demb, 3 stages dsa / dsb, dhead, Markov) depends on the accepted token: no overlap;
 (7) multi-user mode: the P lanes carry P users' AR tokens (N = P): weights / experts shared over the users' expert
     union, attention / index over disjoint KV (U = P x single), rows records as (3); aggregate = P x per-user tok/s.
 (8) P = 1 = the CURRENT die (as built: SM without slot count, no row field, VM column swaps, row-serial records).
     A P-lane die also grows the VM so the N verify / user columns stay resident (+30k words a further column).
Qwen3-8B (TP-8 on d4g, the price-of-record transform ds_die_split._qwen_job + d4g adders): AR = qwen_compiler programme;
DFlash = hgi_sim.dflash.step_program (block B = 16 headline, 8 info; drafter + verify + accept in one step) at position
8,192 - B; the P-lane rules applied per record: SM slots (param [4:2] + 1) cost ceil(slots / P) x the line time (P = 1:
the as-built re-issue, every slot re-issues the line); ATT groups of 4 slots (16 lanes = 4 q heads x 4 slots) merged
ceil(G / P) passes, a merged group pays only its own block rows (context stream once); per-slot records (tag .s<k> /
.c<k>) pay c1 for the first row and II for every further row (row field; P = 1: none); multi-user: the AR programme
with N = P users per record (SM shared, ATT x N streams, rows (3), all-reduce + N x payload at 64 B / cycle).

STATS / AREA: --stats = MTP-STATS summary.json (results/arch/hbm_mtp_next_1018/stats/summary.json), --area = MTP-AREA
summary.json; without --area the added die area is a LABELLED PLACEHOLDER (closed BDC outline floor x 16 SMs x 32 BDCs
a lane + row-field / query-slot / VM estimates of ds_mtp_rows.ITEMS scaled to 16 SMs).

    PYTHONPATH=tools python3 -m hgi_sim.hbm_plane_model --stats S.json [--area A.json] --out DIR [--jobs N] [--quick]
"""
from __future__ import annotations

import argparse
import copy
import datetime
import hashlib
import json
import math
import multiprocessing as mp
import re
import subprocess
from pathlib import Path

from hgi_sim import d4g_price5_1018 as P5      # the d4g pricer (patches V.cost_fn chain + RL.compile_case)
from hgi_sim import d4g_quadrant_1017 as Q
from hgi_sim import plan_study_price_1017 as PS
from hgi_sim import ds_switch_sens as W
from hgi_sim import ds_die_split as S
from hgi_sim import ds_relay_latency as RL
from hgi_sim import ds_mtp_verify as V
from hgi_sim import ds_native_timing as DT
from hgi_sim import timing as T

ROOT = Q.ROOT
CLK = Q.CLK
STAGES = ROOT / "results/arch/hbm_plan_study_1017/stages.json"
DESIGN = ROOT / "results/arch/hbm_mtp_1015/draft_rows/design.json"
P6_RTL = ROOT / "results/arch/hbm_mtp_1015/p6_rtl_2330/measurement.json"
PRICE5 = ROOT / "results/arch/hbm_d4g_price_1017/price5/summary.json"
REF = dict(ds_ar=1905.4, ds_mtp_design=3258.7, qwen_ar=946.2)        # d4g_2ring_qbg, price5/summary.json
PS_LIST = (1, 2, 4, 6, 8)
GAMMA, TAU = 5, 4.159
N_MTP = GAMMA + 1
FUSED_PRE_II_MEAS = 197.0             # (1,451 - 466) / 5, P6 RTL 8fe5d18bd (ds_mtp_verify.row_ii)
VM_WORDS_PER_COLUMN = 30_000          # ds_mtp_verify gap: 6 resident verify columns need ~+150k words
WIN, TOPK_KV = 128, 512
QWEN_TAU = {16: dict(published=8.01, measured=3.656), 8: dict(published=5.584, measured=3.2956)}
BDC_MM2 = 112.32 * 142.56 / 1e6       # closed HBM BDC outline (ds_mtp_rows BDC_LEF), one block-dot unit
NSM = 16


# ------------------------------------------------------------------------------------------------------------------
# inputs: stats (MTP-STATS) and area (MTP-AREA)
# ------------------------------------------------------------------------------------------------------------------
def load_stats(path):
    """-> dict(src, verify_union{N: dict(mean, p90, max)}, users_union{N: mean}, kv_consecutive_measured, tau_walk)"""
    if not path:
        prox = {6: 23.9}
        return dict(src="BRACKET (no --stats): 23.9 continuation proxy (10-16), 36 worst case; users = 6 N worst",
                    verify_union={6: dict(mean=23.9, p90=36.0, max=36.0)},
                    users_union={n: 6.0 * n for n in PS_LIST}, kv_measured=False, tau_walk=None, proxy=prox)
    d = json.loads(Path(path).read_text())
    mu = d["deepseek_moe_union"]
    vu = {}
    for k, v in mu["consecutive_verify"].items():
        if isinstance(v, dict):
            e = v["estimate_decorrelated"]
            vu[int(k)] = dict(mean=e["mean"], p90=e["p90"], max=v["strict_upper_bound"]["max"],
                              strict_mean=v["strict_upper_bound"]["mean"])
    for k, v in mu["consecutive_continuation"].items():       # gamma 7 (P = 8): continuation only
        if int(k) not in vu:
            vu[int(k)] = dict(mean=v["mean"], p90=v["p90"], max=v["max"], strict_mean=None, basis="continuation")
    uu = {int(k): v["mean"] for k, v in mu["independent_users_mixed"].items()}
    uu[1] = 6.0
    kv = d["deepseek_sparse_attention"]["consecutive_positions"].get("measured", False)
    return dict(src=str(path), sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(), verify_union=vu,
                users_union=uu, kv_measured=kv, tau_walk={int(k): v for k, v in d["deepseek_tau_by_P"]
                                                          ["walk_greedy_120_agentic_traces"].items()},
                qwen_tau_by_block=d.get("qwen_dflash", {}).get("tau_by_block_measured"))


def placeholder_area(P):
    """LABELLED PLACEHOLDER die mm2 added over the current d4g for a P-lane die (MTP-AREA replaces it):
    SM: (P - 1) more accumulator lane sets = 16 SMs x 32 block-dot units x the closed BDC outline (FLOOR: the lane
    shares the BDC's multipliers in reality only if the MAC is replicated; IL / slot / control storage unmeasured);
    row field (COLL / SU_DMA / IDX / FUSED / HC items of ds_mtp_rows, 32-SM estimates kept: per-unit, not per-SM);
    attention query slots 0.64 mm2 / 32 SMs x 16 SMs x (P / 6); VM + (max(P, 6) - 1) x 30k words at 1.5 mm2 / 256k."""
    if P == 1:
        return dict(total=0.0, sm=0.0, rows=0.0, att=0.0, vm=0.0)
    sm = (P - 1) * NSM * 32 * BDC_MM2
    rows = 0.02 + 0.05 + 0.10 + 0.10 + 0.15
    att = 0.64 * NSM / 32 * P / 6
    vm = (max(P, N_MTP) - 1) * VM_WORDS_PER_COLUMN * 1.5 / 262144
    return dict(total=round(sm + rows + att + vm, 2), sm=round(sm, 2), rows=rows, att=round(att, 3), vm=round(vm, 3))


def load_area(path):
    if not path:
        return dict(src="PLACEHOLDER (no --area): closed-BDC floor x lanes + ds_mtp_rows item estimates",
                    by_P={P: placeholder_area(P) for P in PS_LIST}, measured=False)
    d = json.loads(Path(path).read_text())
    by = {}
    # accepted shapes: {"die_added_mm2": {"2": x, ...}} | {"by_P": {"2": {"die_added_mm2": x}}} | {"P": {...}}
    for key in ("die_added_mm2", "added_die_mm2", "die_mm2_added"):
        if isinstance(d.get(key), dict):
            by = {int(k): dict(total=float(v)) for k, v in d[key].items()}
    if not by:
        for key in ("by_P", "P", "per_P"):
            if isinstance(d.get(key), dict):
                for k, v in d[key].items():
                    x = v if isinstance(v, (int, float)) else next(
                        (v[f] for f in ("die_added_mm2", "added_die_mm2", "die_mm2_added", "total") if f in v), None)
                    if x is not None:
                        by[int(k)] = dict(total=float(x))
    by.setdefault(1, dict(total=0.0))
    for P in PS_LIST:
        if P not in by:
            by[P] = dict(placeholder_area(P), note="not in --area: placeholder")
    return dict(src=str(path), sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(), by_P=by, measured=True)


# ------------------------------------------------------------------------------------------------------------------
# DeepSeek: d4g environment, P-lane compile, post-pass (measured FUSED II, KV-union attention, per-user index)
# ------------------------------------------------------------------------------------------------------------------
_ENV = {}


def d4g_env():
    if not _ENV:
        st = json.loads(STAGES.read_text())
        st["plan_b_bd"] = Q.bd_stages(st)
        _ENV.update(st=st, vb=PS.VARIANTS["b"], kn=dict(Q.knob(Q.ADDERS, st, ledger=Q.load_ledger()), rings=2,
                                                       ag_qbg=True))
    Q._D4G.clear()
    Q._D4G.update(_ENV["kn"])
    W._DX["dx"] = 0.0                     # 377.6 ns switch crossing (the base)
    W._DX["all"] = False
    W.P.coll_cycles = W._COLL0
    S.set_variant(_ENV["vb"], _ENV["st"])
    return _ENV


def plane_cfg(P, rows_on=True, swap=None):
    """the P-lane die configuration (ds_mtp_rows.cfg_of form); P = 1 = the current die as built"""
    if P == 1 and not rows_on:
        return dict(sm_mode="serial", swap=True, rows=(), att_k=None, sm_k=None)
    if P == 1:                            # current SM, but the row field everywhere (info)
        return dict(sm_mode="serial", swap=True if swap is None else swap,
                    rows=tuple(sorted(set(V.ROW_FAMILIES) - {"ATT"})), att_k=None, sm_k=None)
    return dict(sm_mode="slots", sm_k=P, att_k=P, swap=False if swap is None else swap,
                rows=tuple(sorted(V.ROW_FAMILIES)))


def kv_union_ratio(T_, n, kv, users):
    """U(n) / U(1) for one option-B attention record of n query rows; kv: 'upper' (top-512 disjoint), 'lower' (full
    overlap); users: independent users (disjoint KV, exact)"""
    u1 = T_
    if users:
        return float(n)
    if T_ <= WIN:
        return (WIN + n - 1) / u1
    sel = TOPK_KV * n if kv == "upper" else TOPK_KV
    return (WIN + n - 1 + sel) / u1


def post_pass(prog, N, P, kv, users, bex, bcomp):
    """apply the P-lane rules the base compile_verify does not carry: measured FUSED II, KV-union attention with the
    compiler's pass choice, per-user IDX.INDEX key streams.  -> notes"""
    n_att = n_pre = n_idx = 0
    for r in prog:
        k = getattr(r, "mtp_kind", "")
        if k.startswith("att_B") and k.endswith("_rows"):
            T_ = int(re.match(r"att_B(\d+)_rows", k).group(1))
            op = r.orig_op.split(".")[1].lower()
            full, comp = float(bex[str(T_)][op]), float(bcomp[str(T_)][op])
            fixed = full - comp
            best = None
            for kp in range(max(1, math.ceil(N / P)), N + 1):        # k passes of ~N / k rows (compiler choice)
                sizes = [N // kp + (1 if i < N % kp else 0) for i in range(kp)]
                c = fixed + sum(comp * kv_union_ratio(T_, s, kv, users) for s in sizes)
                best = c if best is None or c < best else best
            r.base_cost = best
            n_att += 1
        elif getattr(r, "ii", None) is not None and r.orig_op == "FUSED.HC_PRE_NORM":
            r.base_cost = r.c1 + (N - 1) * FUSED_PRE_II_MEAS
            r.ii = FUSED_PRE_II_MEAS
            n_pre += 1
        elif users and getattr(r, "ii", None) is not None and r.orig_op == "IDX.INDEX":
            r.base_cost = r.c1 * N            # own key stream a user (no sharing)
            r.ii = r.c1
            n_idx += 1
    return dict(att_rows_records=n_att, fused_pre_measured_ii_records=n_pre, idx_index_per_user_records=n_idx)


def ds_compile(N, cfg, union, kv="upper", users=False):
    c = RL._ctx()
    if N == 1:
        prog, st = V.compile_verify(c["recs"], c["cf"], 1, att="B", bmodel=c["bex"])
        return prog, dict(st)
    prog, st = V.compile_verify(c["recs"], c["cf"], N, sm_mode=cfg["sm_mode"], att="B", bmodel=c["bex"],
                                bcomp=c["bcomp"], swap=cfg["swap"], rows=cfg["rows"], sm_k=cfg["sm_k"],
                                att_k=cfg["att_k"], union=union)
    st = dict(st)
    if cfg["rows"]:
        st.update(post_pass(prog, N, cfg["sm_k"] or 1, kv, users, c["bex"], c["bcomp"]))
    return prog, st


def _run(prog, scale=None):
    P5._count_slots(prog)
    P5._consumers(prog)
    return V.run(prog, scale)


def seed_head_overlap(prog, seed_prog, head_alone, seed_alone):
    """joint S2 schedule of the verify head segment and the next draft's SEED programme (module doc (6))"""
    from hgi_sim import ds_mtp_draft as D
    end = [r for r in prog if r.unit == "CTL" and r.op == "END"][:1]
    head = [r for r in prog if not (r.unit == "CTL" and r.op == "END")
            and not (isinstance(r.layer, int) and r.layer < 40)]
    seed = []
    for r in seed_prog:
        if r.unit == "CTL" and r.op == "END":
            continue
        c = copy.copy(r)
        rd, wr = r.fp
        c.fp = ([V.shift(iv, 1 << 30) for iv in rd], [V.shift(iv, 1 << 30) for iv in wr])
        c.reads = [f"{x}#seed" for x in getattr(r, "reads", ())]
        c.writes = [f"{x}#seed" for x in getattr(r, "writes", ())]
        c.layer = "head"
        seed.append(c)
    out = {}
    T.footprint = V._footprint
    try:
        with D.mtp_dyn():
            for name, seq in (("head_then_seed", head + seed), ("seed_then_head", seed + head)):
                s = T.schedule(V.rebuild([copy.copy(x) for x in seq] + end), DT.POS, "S2", cost_fn=V.cost_fn(None))
                out[name] = round(s["total_cycles"], 1)
    finally:
        T.footprint = V._FP
    joint = min(out.values())
    return dict(head_alone=head_alone, seed_alone=seed_alone, joint=joint, orders=out,
                credit=round(max(0.0, head_alone + seed_alone - joint), 1))


def _mh_ctl():
    smt = json.loads(DESIGN.read_text())["smallest_meeting_target"]["fixed"]
    return smt["step_cycles"] - smt["verify_cycles"] - smt["draft_cycles"] - smt["seed_cycles"]


def ds_job(job):
    """one DeepSeek case -> (name, result)"""
    name, kind, kw = job
    env = d4g_env()
    from hgi_sim import ds_mtp_draft as D
    if kind == "design_check":        # the d4g MTP design point of record (RL.compile_case MTP_design + draft)
        prog = RL.compile_case("MTP_design")
        r = _run(prog)
        d = D.draft_step(RL._ctx()["R"].cfg_of(RL.DESIGN_ITEMS), None)
        step = r["cycles"] + d["draft_cycles"] + d["seed_cycles"] + _mh_ctl()
        return name, dict(verify_cycles=r["cycles"], draft_cycles=d["draft_cycles"], seed_cycles=d["seed_cycles"],
                          step_cycles=round(step, 1), mtp_tok_s=round(TAU * CLK / step, 1))
    if kind == "draft":
        cfg = plane_cfg(kw["P"], rows_on=kw.get("rows_on", kw["P"] > 1))
        d = D.draft_step(cfg, None)
        res = dict(draft_cycles=d["draft_cycles"], draft_by_kind=d["draft_by_kind"], seed_cycles=d["seed_cycles"])
        if kw.get("overlap"):
            vprog, _ = ds_compile(N_MTP, cfg, kw["union"], kw.get("kv", "upper"))
            vr = _run(vprog)
            sprog, _ = D.compile_body("seed", N_MTP, cfg, None)
            res["overlap"] = seed_head_overlap(vprog, sprog, vr["per_segment"]["head"], d["seed_cycles"])
        return name, res
    cfg = plane_cfg(kw["P"], rows_on=kw.get("rows_on", kw["P"] > 1), swap=kw.get("swap"))
    for k in kw.get("drop", ()):     # ablation: remove one feature group
        if k == "SM":
            cfg.update(sm_mode="serial", sm_k=None)
            cfg["att_k"] = 1
        elif k == "VM":
            cfg["swap"] = True
        else:
            cfg["rows"] = tuple(x for x in cfg["rows"] if x not in ABL[k])
    prog, st = ds_compile(kw["N"], cfg, kw.get("union", 6.0), kw.get("kv", "upper"), kw.get("users", False))
    r = _run(prog)
    return name, dict(cycles=r["cycles"], records=r["records"], unit_busy=r["unit_busy"],
                      per_segment=r.get("per_segment"), compile=st, cfg={k: (list(v) if isinstance(v, tuple) else v)
                                                                        for k, v in cfg.items()})


ABL = {"ATT": ("ATT",), "FUSED": ("FUSED.PRE", "FUSED.POST"), "HC": ("HC",), "COLL": ("COLL",),
       "IDX": ("IDX.TOPK", "IDX.INDEX"), "SU_DMA": ("SU", "DMA", "FUSED.QDQ", "ARGMAX")}


# ------------------------------------------------------------------------------------------------------------------
# Qwen3-8B: AR / DFlash / multi-user on the d4g Qwen price (TP-8 transform + d4g adders)
# ------------------------------------------------------------------------------------------------------------------
_T_COST0 = T.cost
SLOT_RE = re.compile(r"\.([sc])(\d+)")
GROUP_RE = re.compile(r"\.g(\d+)$")


def _sm_cost(r, dyn, L, mult):
    """timing.cost SM branch with the line issue x mult (slots re-issued / ceil(slots / P) passes)"""
    bw = T.cv("hbm", "bytes_per_cycle")
    b = r.desc["B"]
    _, n, m, st, _ = T.eff(b, dyn, L)
    tr = T.TRANSPORT if (r.param & 3) == 3 else 1.0
    nbytes = n * m * T.ESZ[b.fmt] * tr
    stream = max(nbytes / bw, -(-m // 32) * n * T.ESZ[b.fmt] * tr / (bw / 32))
    R_ = -(-m // 32)
    lines = math.ceil(T.MEAS["SM.bf16_lines_per_row_k"]["value"] * R_ * n * T.SM_RATE) * mult
    comp = lines + T.MEAS["SM.drain"]["value"]
    fa = T.MEAS["hbm.first_access"]["value"] + T.MEAS["SM.overhead"]["value"]
    return fa + max(comp, stream)


def _att_stream(r, dyn, L):
    b = r.desc["B"]
    _, n, _, _, _ = T.eff(b, dyn, L)
    return n * 128 * T.ESZ[b.fmt] / T.cv("hbm", "bytes_per_cycle")


def _row_ii(r, dyn, L, c):
    """II of a further row of a Qwen record (row field)"""
    u, op = r.unit, r.op
    if u == "SU":
        _, how = T.su_cost(r, dyn, L)
        m = re.search(r"nv (\d+)", how)
        return float(m.group(1)) if m else c
    if u == "FUSED":                  # LL lanes: 4,096 words at the measured P6 II per 5,120 words
        return min(c, FUSED_PRE_II_MEAS * 4096 / 5120)
    if u == "DMA" and op == "LOAD":
        return max(2.0, c - T.first_access())
    if u == "COLL" and op == "ARGMAX_MERGE":
        return 2.0
    if u == "COLL":
        return r.desc["A"].n / 16.0       # 64 B / cycle endpoint serialisation (dflash_timing estimate)
    if u == "ARGMAX":
        return max(1.0, c - 20.0)
    return c                          # SFU, STORE, CTL: no row saving priced


def qwen_plane_cost(mode, P, N, groups, att_g=1):
    """the P-lane per-record transform of timing.cost (module doc, Qwen)"""
    dfc = None
    if mode == "dflash":
        from hgi_sim import dflash_timing as DFT
        dfc = DFT.make_cost("spec", False)

    def cost(r, dyn, L, cfg=None):
        u, tag = r.unit, r.tag or ""
        if dfc and (u == "ATT" or (u == "COLL" and r.op in ("ALL_REDUCE_SUM", "ALL_GATHER")) or
                    (u == "CTL" and r.op == "TOKX")):
            c, g, how = dfc(r, dyn, L)    # dflash_timing: ATT B + C rows, payload-dependent collectives, TOKX beats
        else:
            c, g, how = _T_COST0(r, dyn, L)
        if u == "SM":
            slots = N if mode == "mu" else r.desc["A"].m      # x rows = slots (param [4:2] is 3 b: R <= 8 only)
            mult = slots if P == 1 else math.ceil(slots / P)
            if mult != 1:
                c = _sm_cost(r, dyn, L, mult)
            return c, g, how
        if mode == "mu":
            if N == 1:
                return c, g, how
            if u == "ATT":
                return c + (N - 1) * _att_stream(r, dyn, L), g, how
            if u == "CTL":
                return c, g, how
            return c + (N - 1) * _row_ii(r, dyn, L, c), g, how
        if P == 1:
            return c, g, how
        if u == "ATT":
            m = GROUP_RE.search(tag)
            if m:
                j = int(m.group(1)) // att_g     # tag .g<s0> carries the first SLOT; group index = s0 / G (QCHK)
                if j % P:                 # merged into the pass of group j - j % P: context lines streamed once
                    c = max(0.0, c - _att_stream(r, dyn, L))
            return c, g, how
        m = SLOT_RE.search(tag)
        if m and u != "SM":
            key = SLOT_RE.sub(r".\1#", tag)
            if int(m.group(2)) != groups.get(key, 0):
                c = _row_ii(r, dyn, L, c)
        return c, g, how
    return cost


def qwen_job(job):
    name, mode, kw = job
    env = d4g_env()
    from hgi_sim import qwen_timing as QT
    cfg = json.loads(QT.CFG.read_text())
    md = QT.QC.qwen_params(cfg)
    if mode == "dflash":
        from hgi_sim import dflash as DF
        dcfg = json.loads((ROOT / "compiler/models/qwen3-8b-dflash-b16/config.json").read_text())
        B = kw["B"]
        pos = 8192 - B
        # QCHK 10-18: on a P-lane die the compiler chooses the record size R (slots a record: SM.MATVEC slot field
        # widened to 4 b, N <= 16, RTL change list SM/ISA) among R in {P, 8, 16}: an SM record of R slots costs
        # ceil(R / P) line passes behind ONE first access, and the per-pass records (norm / row-scale SU /
        # all-reduce, payload R x H) are issued ceil(B / R) times.  The LM head takes R-slot passes too (the logits
        # stream SM -> SU -> ARGMAX; ARGMAX.LOCAL row field N = R running maxima).  The as-built split (R = 8,
        # head 4) made P = 6 cost ceil(8 / 6) x 2 = 4 weight passes (= P 4) and every head 4 passes at any P.
        # P = 1 keeps the as-built split (every slot re-issues the line).
        R = kw.get("R")
        # VM: the P-lane die's VM growth (+ (P - 1) x 30k words, VM item) bounds R; an R that does not fit is not a
        # choice (R = 16 needs ~410k words: P >= 6)
        # The head pass PH = the largest of {16, 8, 6, 4} (<= B) whose VM map fits (the map keeps PH x 37,984 logit
        # words, TP4 layout: conservative for the TP-8 price).
        s0_, h0_, v0_ = DF.SM_MAX_SLOTS, DF.HEAD_SLOTS, DF.VM_WORDS
        g = None
        try:
            if R and kw["P"] > 1:
                DF.SM_MAX_SLOTS = R
                DF.VM_WORDS = (1 << 18) + (kw["P"] - 1) * VM_WORDS_PER_COLUMN
                for ph in (16, 8, 6, 4):
                    if ph > B:
                        continue
                    DF.HEAD_SLOTS = ph
                    try:
                        g = DF.DGeom(cfg, dcfg, 8192, B)
                        break
                    except AssertionError as ex:
                        unfit = str(ex)
                if g is None:
                    return name, dict(cycles=float("inf"), vm_unfit=unfit)
            else:
                g = DF.DGeom(cfg, dcfg, 8192, B)
            recs = DF.step_program(g, md, timing_pos=pos)
        finally:
            DF.SM_MAX_SLOTS, DF.HEAD_SLOTS, DF.VM_WORDS = s0_, h0_, v0_
        rec_info = dict(record_slots=g.P, head_slots=g.PH, vm_words=g.vm_end)
        att_g = g.G
    else:
        pos = 8191
        att_g = 1
        rec_info = {}
        recs = QT.QC.program(QT.QC.Geometry(cfg, 8192), md, cfg["num_hidden_layers"])
    groups = {}
    for r in recs:
        m = SLOT_RE.search(r.tag or "")
        if m:
            key = SLOT_RE.sub(r".\1#", r.tag)
            groups[key] = min(groups.get(key, 1 << 30), int(m.group(2)))
    base = qwen_plane_cost(mode, kw["P"], kw.get("N", 1), groups, att_g)
    # Q._qwen: the d4g adders on the unit cost (Qwen full precision: no QBG); S._qwen_job: relay knob + TP-8 split
    q = env["vb"].get("qwen") or {}
    kq = dict(env["kn"], G1=q.get("G1", 8), lanes=q.get("lanes", 4))
    kq.pop("ag_qbg", None)
    kq.pop("ag_fp8", None)

    def unit(r, dyn, L, cfg=None):
        c, g, how = base(r, dyn, L, cfg)
        return c + Q.d4g_added(r, c, kq), g, how
    kn = RL._knob(env["st"]["v5"], env["st"][env["vb"]["stages"]])
    fa = S.first_access()
    mf = T.MEAS.get("SM.overhead", {}).get("value", 0) + fa

    def cf(r, dyn, L):
        c, g, how = unit(r, dyn, L)
        c += RL.added(r, kn["delta"], False, None, kn["b"], kn["o"])
        if q:
            if r.unit in ("SM", "ATT") and q["sm_s"] != 1 and c > mf:
                c = mf + q["sm_s"] * (c - mf)
            elif r.unit == "DMA" and r.op == "LOAD" and c > fa:
                c = fa + q["bw_s"] * (c - fa)
            elif r.unit == "COLL":
                n = r.desc["A"].n if "A" in r.desc else 1
                if mode == "mu":
                    n *= kw.get("N", 1)
                k = 2 if r.op == "ALL_REDUCE_SUM" else 1
                f0 = max(1, math.ceil(n * 2 / q["G0"] / 64))
                f1 = max(1, math.ceil(n * 2 / q["G1"] / 64))
                c += k * (S.deliver(f1, q["G1"], q["lanes"]) - S.deliver(f0, q["G0"], S.LANES0)) + \
                    k * q.get("xc", 0) * S.CROSS
        return c, g, how
    s = T.schedule(recs, pos, "S2", cost_fn=cf)
    busy = {u: round(v["busy"], 1) for u, v in s["per_unit"].items()}
    return name, dict(cycles=round(s["total_cycles"], 1), records=len(recs), unit_busy=busy, position=pos, **rec_info,
                      races=len(s.get("races", [])))


def _any(job):
    return qwen_job(job[1:]) if job[0] == "qwen" else ds_job(job[1:])


# ------------------------------------------------------------------------------------------------------------------
# job matrix + composition
# ------------------------------------------------------------------------------------------------------------------
def jobs_for(stats, quick=False):
    vu, uu = stats["verify_union"], stats["users_union"]
    u6 = vu[N_MTP]
    J = [("ds", "ds|AR", "verify", dict(P=1, N=1)),
         ("ds", "ds|design_check", "design_check", {})]
    for P in PS_LIST:
        J.append(("ds", f"ds|MTP|P{P}", "verify", dict(P=P, N=N_MTP, union=u6["mean"], kv="upper")))
        J.append(("ds", f"ds|draft|P{P}", "draft", dict(P=P, overlap=P > 1, union=u6["mean"])))
        if P > 1:
            J.append(("ds", f"ds|MU|P{P}", "verify", dict(P=P, N=P, union=uu.get(P, 6.0 * P), users=True)))
    if quick:
        return J
    for P in PS_LIST[1:]:
        J.append(("ds", f"ds|MTP_kvlow|P{P}", "verify", dict(P=P, N=N_MTP, union=u6["mean"], kv="lower")))
        J.append(("ds", f"ds|MTP_up90|P{P}", "verify", dict(P=P, N=N_MTP, union=u6["p90"], kv="upper")))
    J.append(("ds", "ds|MTP_max36|P6", "verify", dict(P=6, N=N_MTP, union=u6["max"], kv="upper")))
    J.append(("ds", "ds|MTP_rowsonly|P1", "verify", dict(P=1, N=N_MTP, union=u6["mean"], rows_on=True)))
    J.append(("ds", "ds|draft_rowsonly|P1", "draft", dict(P=1, rows_on=True)))
    for P in (2, 4):                  # compiler choice gamma = P - 1 (N = P, one SM pass)
        if P in vu:
            J.append(("ds", f"ds|MTPg|P{P}", "verify", dict(P=P, N=P, union=vu[P]["mean"], kv="upper")))
    for k in ("SM", "VM", *ABL):
        J.append(("ds", f"ds|abl_{k}|P6", "verify", dict(P=6, N=N_MTP, union=u6["mean"], kv="upper", drop=(k,))))
    J.append(("qwen", "qwen|AR", "ar", dict(P=1)))
    for P in PS_LIST:
        for B in (16, 8):
            if P == 1:
                J.append(("qwen", f"qwen|DFlash{B}|P{P}", "dflash", dict(P=P, B=B)))
            for R in sorted({min(B, x) for x in (P, 2 * P, 8, 16)}) if P > 1 else ():
                J.append(("qwen", f"qwen|DFlash{B}|P{P}|R{R}", "dflash", dict(P=P, B=B, R=R)))
        if P > 1:
            J.append(("qwen", f"qwen|MU|P{P}", "mu", dict(P=P, N=P)))
    return J


def pick_record_size(res):
    """the compiler's record-size choice: qwen|DFlash<B>|P<P> = the fastest qwen|DFlash<B>|P<P>|R<R> (QCHK 10-18)"""
    best = {}
    for k, v in res.items():
        m = re.match(r"(qwen\|DFlash\d+\|P\d+)\|R(\d+)$", k)
        if m and (m.group(1) not in best or v["cycles"] < best[m.group(1)][1]["cycles"]):
            best[m.group(1)] = (int(m.group(2)), v)
    for k, (R, v) in best.items():
        res[k] = dict(v, record_slots_tried={int(kk.rsplit("R", 1)[1]): res[kk]["cycles"]
                                             for kk in res if kk.startswith(k + "|R")})
    for v in res.values():                # an R whose VM map does not fit: no time (JSON null, not Infinity)
        for d_ in (v, v.get("record_slots_tried") or {}):
            for kk, x in d_.items():
                if isinstance(x, float) and math.isinf(x):
                    d_[kk] = None
    return res


def compose(res, stats, area):
    mh = _mh_ctl()
    ar = res["ds|AR"]["cycles"]
    qar = res["qwen|AR"]["cycles"]
    rows, units = [], {}
    tw = stats.get("tau_walk") or {}

    def mtp(vkey, P, overlap=True):
        v = res[vkey]["cycles"]
        d = res[f"ds|draft|P{P}"]
        ov = d.get("overlap", {}).get("credit", 0.0) if overlap else 0.0
        step = v + d["draft_cycles"] + d["seed_cycles"] + mh - ov
        return step, v, d, ov
    for P in PS_LIST:
        step, v, d, ov = mtp(f"ds|MTP|P{P}", P)
        row = dict(P=P, die_added_mm2=area["by_P"][P]["total"],
                   ds_ar_tok_s=round(CLK / ar, 1),
                   ds_mtp_tok_s=round(TAU * CLK / step, 1),
                   ds_mtp_step_cycles=round(step, 1), ds_verify_cycles=v, ds_draft_cycles=d["draft_cycles"],
                   ds_seed_cycles=d["seed_cycles"], ds_seed_head_overlap_credit=ov, ds_mh_ctl_cycles=round(mh, 1),
                   ds_mtp_over_ar=round(TAU * ar / step, 3))
        for tag, key in (("kv_lower", "MTP_kvlow"), ("union_p90", "MTP_up90")):
            if f"ds|{key}|P{P}" in res:
                s2 = mtp(f"ds|{key}|P{P}", P)[0]
                row[f"ds_mtp_tok_s_{tag}"] = round(TAU * CLK / s2, 1)
        if f"ds|MTPg|P{P}" in res and tw:
            g = P - 1
            tau_g = TAU * tw[g] / tw[GAMMA]
            s2 = mtp(f"ds|MTPg|P{P}", P)[0]
            row["ds_mtp_gammaP_tok_s"] = round(tau_g * CLK / s2, 1)
            row["ds_mtp_gammaP_note"] = f"gamma {g} (N = {P}), tau {tau_g:.3f} = 4.159 x walk[{g}] / walk[5]"
        if P == 1:
            mu = dict(cycles=ar)
        else:
            mu = res.get(f"ds|MU|P{P}")
        if mu:
            row["ds_mu_aggregate_tok_s"] = round(P * CLK / mu["cycles"], 1)
            row["ds_mu_per_user_tok_s"] = round(CLK / mu["cycles"], 1)
        row["qwen_ar_tok_s"] = round(CLK / qar, 1)
        for B in (16, 8):
            k = f"qwen|DFlash{B}|P{P}"
            if k in res:
                c = res[k]["cycles"]
                row[f"qwen_dflash{B}_step_cycles"] = c
                row[f"qwen_dflash{B}_step_over_ar"] = round(c / qar, 3)
                if res[k].get("record_slots"):
                    row[f"qwen_dflash{B}_record_head_slots"] = [res[k]["record_slots"], res[k]["head_slots"]]
                for tk, tv in QWEN_TAU[B].items():
                    row[f"qwen_dflash{B}_tok_s_{tk}"] = round(tv * CLK / c, 1)
        qmu = dict(cycles=qar) if P == 1 else res.get(f"qwen|MU|P{P}")
        if qmu:
            row["qwen_mu_aggregate_tok_s"] = round(P * CLK / qmu["cycles"], 1)
            row["qwen_mu_per_user_tok_s"] = round(CLK / qmu["cycles"], 1)
        rows.append(row)
        units[P] = dict(ds_mtp_verify=res[f"ds|MTP|P{P}"]["unit_busy"],
                        qwen_dflash16=res.get(f"qwen|DFlash16|P{P}", {}).get("unit_busy"),
                        ds_mu=(res.get(f"ds|MU|P{P}") or {}).get("unit_busy"))
    # per-layer P choice by the compiler: per layer segment, the best lane count <= P (same N, row field on)
    seg = {P: res[f"ds|MTP|P{P}"].get("per_segment") or {} for P in PS_LIST}
    if "ds|MTP_rowsonly|P1" in res:
        seg[1] = res["ds|MTP_rowsonly|P1"].get("per_segment") or {}
    perlayer = {}
    for P in PS_LIST[1:]:
        cand = [p for p in seg if p <= P and seg[p]]
        tot = sum(min(seg[p][k] for p in cand if k in seg[p]) for k in seg[P])
        perlayer[P] = dict(verify_cycles=round(tot, 1), vs_uniform=round(tot - res[f"ds|MTP|P{P}"]["cycles"], 1),
                           lanes_used={k: min(cand, key=lambda p: seg[p].get(k, 1e18)) for k in seg[P]})
    abl = {}
    base6 = res["ds|MTP|P6"]["cycles"]
    for k in ("SM", "VM", *ABL):
        x = res.get(f"ds|abl_{k}|P6")
        if x:
            abl[k] = dict(verify_cycles_without=x["cycles"], cycles_saved_by_feature=round(x["cycles"] - base6, 1))
    return dict(table=rows, unit_busy=units, per_layer_choice=perlayer, ablation_P6=abl)


RTL_CHANGES = [
    ("SM", "abl_SM", "H-SM", "P accumulator lanes per MAC column: each HBM weight word / BDC line broadcast to P lanes "
     "(P x MAC, same 99 B/cycle/SM HBM share, SMEM and VM ports); SM.MATVEC slot field (HGI-1 spec 6.7 param [4:2] = "
     "N - 1, widen to 4 b for N <= 16) + per-slot x base; P x-slot stores; per-lane result publish (slot-major)"),
    ("ATT", "abl_ATT", "H-SM (SM attention)", "KV-line-stationary multi-query attention: P query slots a SM engine, each "
     "KV line streamed once and applied to the lanes whose top-k mask selects it (per-line lane mask from the N IDX "
     "top-k lists + window rule), per-lane QK / PV accumulators, fixed spans (first access, dispatch, publish, "
     "cross-SM merge) once a record"),
    ("FUSED", "abl_FUSED", "H-SU (FUSED)", "FUSED.HC_PRE_NORM / HC_POST row field N on the LL lanes: gain sectors kept "
     "across rows, two r slots (row p+1 phase A over row p's tail), per-row scalar set; MEASURED II 197 (P6 RTL)"),
    ("HC", "abl_HC", "H-SU (HC)", "HC.HC_MIX N rows streamed against stationary mix weights (HCP x6 mode II 250) + "
     "Sinkhorn x 3 units (II 634 / 3)"),
    ("COLL", "abl_COLL", "H-COLL", "COLL ROW_GATHER / TOPK_MERGE / kv gather / ARGMAX_MERGE take N rows (one message "
     "train, endpoint / crossing / tail once); shared ALL_GATHER / GROUP_REDUCE_MCAST carry N x payload; ring AG "
     "flits x N (d4g adders unchanged per record)"),
    ("IDX", "abl_IDX", "H-IDX", "IDX.INDEX N queries over ONE key stream (N x 4,096-word query store), IDX.TOPK heap "
     "row reset, verify expert-UNION record (384-b union bitmap, per-expert lane lists for the grouped GEMM)"),
    ("SU_DMA", "abl_SU_DMA", "H-SU / H-DIE / H-IDX", "row counters in SU.VOP (indexed + un-indexed), SFU chains, "
     "DMA.KVWB_DS (N rows, window ring 256 slots: +128 HBM rows a layer), position-addressed DMA.LOAD rows, FUSED.QDQ, "
     "ARGMAX.LOCAL"),
    ("VM", "abl_VM", "H-DIE", "VM capacity: N resident verify / user columns (h + PRE): + (N - 1) x ~30k words "
     "(N = 6: ~+150k words, VM 2^18 -> ~2^18.9; 4 quadrant slices); else per-layer column swaps"),
    ("ISA", None, "H-ISA", "record header row count N (all units) + per-row descriptor stride; CTL.TOKX (k completion "
     "beats, SPEC_GAP Q-MTP-1)"),
    ("DRAFT", None, "H-MTP", "DSpark draft on the same die: dsa / dsb / dhead as R = 5-row records (no new unit), "
     "SEED of the next step scheduled with the verify head (joint S2 schedule), Markov / demb serial"),
]


def summarize(out):
    """condensed summary.json + README.md text from a full run record"""
    t = out["table"]
    abl = out.get("ablation_P6", {})
    ch = []
    for unit, k, owner, what in RTL_CHANGES:
        x = abl.get(unit) if k else None
        ch.append(dict(unit=unit, owner=owner, change=what,
                       verify_cycles_saved_P6=(x or {}).get("cycles_saved_by_feature"),
                       saved_basis="P = 6 headline verify with this feature removed (ds|abl_*), cycles a DSpark step"
                       if x else "not separately ablated"))
    st = out["stats"]
    summ = dict(
        schema="opentallas.hbm_mtp_next_1018.model_summary.v1", lane="HBM-MTP / MTP-MODEL", date="2026-10-18",
        tool="tools/hgi_sim/hbm_plane_model.py", git_head=out.get("git_head"), generated_utc=out["generated_utc"],
        price_basis="d4g plan (b) price of record: HBM-PRICE5 d4g_2ring_qbg (two rings + QBG, RTL1/2 ledger), S2 CP "
                    "schedule per layer segment; option-B attention on the SM engines (measured spans)",
        validation=out.get("validation"),
        stats=dict(src=st.get("src"), sha256=st.get("sha256"), verify_union_P6=st["verify_union"].get(6),
                   users_union=st["users_union"], kv_consecutive_measured=st.get("kv_measured")),
        area=dict(src=out["area"]["src"], measured=out["area"]["measured"],
                  by_P={str(k): v for k, v in out["area"]["by_P"].items()}),
        table=t, per_layer_choice=out.get("per_layer_choice"), ablation_P6=abl, rtl_change_list=ch,
        unit_busy=out.get("unit_busy"),
        assumptions=[
            "P = 1 = the current d4g die AS BUILT (SM without slot count, no row field, VM column swaps, row-serial "
            "draft); P >= 2 = P lanes + row field N + VM-resident columns",
            "DS MTP: DSpark gamma 5, N = 6 verify positions, tau 4.159 (owner 6-class blend) at every P; P = 8 leaves "
            "2 lanes idle for MTP (no gamma-7 drafter); ds_mtp_gammaP rows = the compiler choosing gamma = P - 1 with "
            "tau scaled by the MTP-STATS greedy walk",
            "expert union: MTP-STATS decorrelated verify estimate (P = 6 mean) headline, p90 as bracket; users: "
            "independent users mixed workloads mean",
            "KV top-512 overlap of consecutive positions is UNMEASURED: headline at the upper bound (N x 512 selected "
            "+ 128 + N - 1 window lines), kv_lower = full overlap (512 + window); users: N x single (exact)",
            "row II: FUSED.HC_PRE_NORM measured 197 (P6 RTL); all other II PRICED from tables / structure "
            "(ds_mtp_verify.row_ii): FUSED.POST 100, QDQ n/32, HC max(250 HCP x6 measured, Sinkhorn 634/3), COLL "
            "c1 - 741.7 fixed, IDX.TOPK 47, IDX.INDEX c1 x 152/658.9 (users: c1), SU nv, DMA c1 - first access, "
            "ARGMAX 6; Qwen ROW_NORM 157.6 (anchor scaled 4096/5120), SU nv, all-reduce n/16 (64 B/cycle)",
            "DSpark draft at P lanes = R = 5-row records (ds_mtp_draft, stage expert union = no sharing 15); seed "
            "overlap = joint S2 schedule with the verify head, nothing after the accept overlaps",
            "Qwen DFlash: dflash.step_program B = 16 (8 info) at pos 8,192 - B, tau published 8.01 (b16) / 5.584 "
            "(b8, anchored) and measured cycle-weighted 3.656 / 3.2956; ATT 4-slot groups (16 lanes) are the current "
            "record form, a P-lane engine streams the context once for P groups (QCHK fix: group index = slot / 4); "
            "P = 1 = every slot re-issues the SM line; P >= 2 = the compiler's record size R in {P, 2P, 8, 16} "
            "(SM ceil(R / P) line passes a record, ceil(B / R) per-pass records) and head pass PH in {16, 8, 6, 4}, "
            "largest that fits the P-lane VM (2^18 + (P - 1) x 30k words; TP4 map, conservative) (QCHK 10-18: the "
            "as-built 8-slot / 4-slot head split had made P = 6 = P = 4)",
            "multi-user: all users at the same position (DS 1M, Qwen 8K); HBM capacity for P users' 1M KV NOT checked",
            "area: " + ("MTP-AREA measured" if out["area"]["measured"] else
                        "PLACEHOLDER (closed BDC outline floor x 16 SMs x 32 BDCs a lane + item estimates); "
                        "the composer re-runs with MTP-AREA"),
        ],
        rerun="PYTHONPATH=tools python3 -m hgi_sim.hbm_plane_model --stats results/arch/hbm_mtp_next_1018/stats/"
              "summary.json [--area results/arch/hbm_mtp_next_1018/sm_area/summary.json] --out "
              "results/arch/hbm_mtp_next_1018/model  (heavy: ~60 S2 schedules, run on the fleet, ~15 min at 24 jobs)",
        sources_sha256=out.get("sources_sha256"))
    return summ


def readme(s):
    t = s["table"]
    v = s["validation"] or {}
    L = ["# HBM P-lane die: compiler timing model (MTP-MODEL, 10-18)", "",
         "Design study outside the release closure (lane HBM-MTP). Tool `tools/hgi_sim/hbm_plane_model.py`; full "
         "record `run.json`, condensed `summary.json`.", "",
         f"Price basis: {s['price_basis']}.", "",
         "Validation: P = 1 DS AR " + f"{v.get('ds_ar_tok_s')} tok/s vs {v.get('ds_ar_ref')} of record "
         f"({v.get('ds_ar_err_pct')} %); Qwen AR {v.get('qwen_ar_tok_s')} vs {v.get('qwen_ar_ref')} "
         f"({v.get('qwen_ar_err_pct')} %); the d4g MTP design point re-priced through the same chain: "
         f"{(v.get('ds_mtp_design_point') or {}).get('mtp_tok_s')} vs {v.get('ds_mtp_design_ref')}.", "",
         f"Stats: {s['stats']['src']}. Area: {s['area']['src']}.", "",
         "## tok/s vs P", "",
         "| P | +mm2 | DS AR | DS MTP (KV upper) | DS MTP kv-lower | DS MTP union p90 | DS users agg / per-user "
         "| Qwen AR | Qwen DFlash b16 pub 8.01 / meas 3.656 | Qwen b8 pub / meas | Qwen users agg / per-user |",
         "|---:|---:|---:|---:|---:|---:|---|---:|---|---|---|"]
    for r in t:
        L.append(f"| {r['P']} | {r['die_added_mm2']} | {r['ds_ar_tok_s']} | **{r['ds_mtp_tok_s']}** | "
                 f"{r.get('ds_mtp_tok_s_kv_lower', '')} | {r.get('ds_mtp_tok_s_union_p90', '')} | "
                 f"{r.get('ds_mu_aggregate_tok_s')} / {r.get('ds_mu_per_user_tok_s')} | {r['qwen_ar_tok_s']} | "
                 f"{r.get('qwen_dflash16_tok_s_published')} / {r.get('qwen_dflash16_tok_s_measured')} | "
                 f"{r.get('qwen_dflash8_tok_s_published')} / {r.get('qwen_dflash8_tok_s_measured')} | "
                 f"{r.get('qwen_mu_aggregate_tok_s')} / {r.get('qwen_mu_per_user_tok_s')} |")
    L += ["", "DS MTP step terms (cycles):", "", "| P | verify | draft | seed | seed/head overlap credit | step | "
          "MTP/AR | gamma = P-1 option |", "|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in t:
        L.append(f"| {r['P']} | {r['ds_verify_cycles']} | {r['ds_draft_cycles']} | {r['ds_seed_cycles']} | "
                 f"{r['ds_seed_head_overlap_credit']} | {r['ds_mtp_step_cycles']} | {r['ds_mtp_over_ar']} | "
                 f"{r.get('ds_mtp_gammaP_tok_s', '')} {r.get('ds_mtp_gammaP_note', '')} |")
    pl = s.get("per_layer_choice") or {}
    if pl:
        L += ["", "Compiler per-layer lane choice (best lanes <= P per layer segment, row field on): verify cycles "
              + ", ".join(f"P{k}: {x['verify_cycles']} ({x['vs_uniform']:+})" for k, x in pl.items()) + "."]
    L += ["", "## Per-unit RTL change list (cycles saved = P = 6 headline verify with the feature removed)", "",
          "| unit | owner | change | verify cycles saved a step (P = 6) |", "|---|---|---|---:|"]
    for c in s["rtl_change_list"]:
        L.append(f"| {c['unit']} | {c['owner']} | {c['change']} | {c['verify_cycles_saved_P6'] or '-'} |")
    ub = (s.get("unit_busy") or {})
    L += ["", "## Verify unit busy (DS MTP, cycles summed over layer segments)", "",
          "| P | " + " | ".join(sorted(next(iter(ub.values()))["ds_mtp_verify"])) + " |",
          "|---:|" + "---:|" * len(next(iter(ub.values()))["ds_mtp_verify"])] if ub else []
    for P, x in ub.items():
        u = x["ds_mtp_verify"]
        L.append(f"| {P} | " + " | ".join(str(u[k]) for k in sorted(u)) + " |")
    L += ["", "## Assumptions", ""] + [f"- {a}" for a in s["assumptions"]]
    L += ["", "## Re-run", "", f"`{s['rerun']}`", "", "Re-summarise a run record without re-timing: "
          "`python3 -m hgi_sim.hbm_plane_model --from-run results/arch/hbm_mtp_next_1018/model/run.json "
          "[--area A.json] --out results/arch/hbm_mtp_next_1018/model`", ""]
    return "\n".join(L)


def git_sha():
    try:
        return subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        import os
        return os.environ.get("OT_GIT_HEAD")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stats", type=Path)
    ap.add_argument("--area", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--jobs", type=int, default=24)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--only", default="", help="comma list of job names (debug)")
    ap.add_argument("--from-run", type=Path, help="re-compose + summarise an existing run.json (no re-timing)")
    a = ap.parse_args()
    if a.from_run:
        out = json.loads(a.from_run.read_text())
        out["stats"]["verify_union"] = {int(k): v for k, v in out["stats"]["verify_union"].items()}
        out["stats"]["users_union"] = {int(k): v for k, v in out["stats"]["users_union"].items()}
        if out["stats"].get("tau_walk"):
            out["stats"]["tau_walk"] = {int(k): v for k, v in out["stats"]["tau_walk"].items()}
        out["area"] = load_area(a.area) if a.area else dict(out["area"], by_P={int(k): v for k, v in
                                                                               out["area"]["by_P"].items()})
        out.update(compose(out["runs"], out["stats"], out["area"]))
        return write_out(out, a.out)
    stats = load_stats(a.stats)
    area = load_area(a.area)
    J = jobs_for(stats, a.quick)
    if a.only:
        keep = set(a.only.split(","))
        J = [j for j in J if j[1] in keep]
    J.sort(key=lambda j: 0 if ("draft" in j[1] or "MU|P8" in j[1] or "MTP|P" in j[1]) else 1)
    with mp.Pool(a.jobs) as pool:
        res = dict(pool.imap_unordered(_any, J, chunksize=1))
    res = pick_record_size(res)
    out = dict(schema="opentallas.hbm_mtp_next_1018.model.v1",
               generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               git_head=git_sha(), rule=__doc__, stats=stats, area=area, reference_price_of_record=REF, runs=res)
    if "ds|AR" in res and "qwen|AR" in res and not a.only:
        out.update(compose(res, stats, area))
        ar, qar = out["table"][0]["ds_ar_tok_s"], out["table"][0]["qwen_ar_tok_s"]
        out["validation"] = dict(
            ds_ar_tok_s=ar, ds_ar_ref=REF["ds_ar"], ds_ar_err_pct=round(100 * (ar / REF["ds_ar"] - 1), 3),
            qwen_ar_tok_s=qar, qwen_ar_ref=REF["qwen_ar"], qwen_ar_err_pct=round(100 * (qar / REF["qwen_ar"] - 1), 3),
            ds_mtp_design_point=res.get("ds|design_check"), ds_mtp_design_ref=REF["ds_mtp_design"])
    srcs = ["tools/hgi_sim/hbm_plane_model.py", "tools/hgi_sim/ds_mtp_verify.py", "tools/hgi_sim/ds_mtp_draft.py",
            "tools/hgi_sim/ds_mtp_rows.py", "tools/hgi_sim/d4g_price5_1018.py", "tools/hgi_sim/d4g_quadrant_1017.py",
            "tools/hgi_sim/dflash.py", "tools/hgi_sim/timing.py", "results/arch/hgi_programs_20261010/inputs/ds_rank0_program.json",
            "results/arch/hbm_plan_study_1017/stages.json", "results/arch/hbm_d4g_price_1017/latency_ledger.json",
            "results/hbm_sm_attention_1015/b_measured_model.json", "results/arch/hbm_mtp_1015/draft_rows/draft_bodies.json",
            "results/arch/hbm_mtp_1015/p6_rtl_2330/measurement.json", "results/arch/hbm_d4g_price_1017/price5/summary.json"]
    out["sources_sha256"] = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in srcs if (ROOT / p).exists()}
    if "table" not in out:
        print(json.dumps({k: (v.get("cycles") if isinstance(v, dict) else v) for k, v in res.items()}, indent=1))
        if a.out:
            a.out.mkdir(parents=True, exist_ok=True)
            (a.out / "run.json").write_text(_dump(out))
        return 0
    return write_out(out, a.out)


def _dump(o):
    return json.dumps(o, indent=1, default=lambda x: sorted(x) if isinstance(x, set) else str(x)) + "\n"


def write_out(out, d):
    s = summarize(out)
    if d:
        d.mkdir(parents=True, exist_ok=True)
        (d / "run.json").write_text(_dump(out))
        (d / "summary.json").write_text(_dump(s))
        (d / "README.md").write_text(readme(s))
    print(json.dumps(dict(validation=s["validation"], table=s["table"]), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
