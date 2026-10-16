#!/usr/bin/env python3
"""DeepSeek-V4.1-Flash DSpark MTP on the generic HBM die at 1M context: the BATCHED VERIFY program (P = gamma + 1
positions in one layer-major pass) compiled from the bit-exact native HGI-1 AR token program, timed with the command
processor modelled (timing.schedule S2), plus the DSpark draft / seed / accept terms, -> cycles a step and tok/s at tau.

Compiler pass (verify(P)): the native rank-0 AR program (hgi_sim.ds_native --program-out, bit-exact against the
released checkpoint at position 1,048,575) is rewritten record by record, in program order:
  SHARED once for all P positions (one record, operands of every position):
    SM.MATVEC  sm_mode "pport": one weight read serves P slots (HGI-1 spec 6.7, record param [4:2] = P - 1; the slots
               ride the SM's per-column x stores, issue unchanged -- dflash_timing 'spec' rule, the Qwen DFlash basis);
               sm_mode "serial": the AS-BUILT smh ports carry op_xb only (no slot count) -> P single-slot records.
    routed MoE experts: the verify reads the UNION of the P positions' top-6 experts: U slots a die (each P_e = 6P/U
               positions; U = the measured greedy-continuation union 23.9 of 36 at P = 6, results/speculative/
               v41_dspark_verify_union_parent_review_20261003: a proxy, HELD as conditional), + 1 union record a layer
               (priced as the route top-6 IDX record); the shared expert slot serves all P.
    COLL.ALL_GATHER / GROUP_REDUCE_MCAST: one collective of P x the bytes (perf.coll_cycles ratio on the record price).
    SU.VOP without an index operand: rows x P in one record (timing.su_cost layout model at m x P).
    DMA.LOAD of position-independent constants (gains, biases, tables), DMA.FENCE, CTL.
  PER POSITION (P records): ATT.QK / ATT.PV (own KV selection), IDX.*, FUSED.* (HC pre-norm / post / QDQ), HC.*,
    DMA.KVWB_DS / indexed or position-addressed loads, SU with an index operand, COLL.ROW_GATHER / TOPK_MERGE /
    kv_gather / ARGMAX_MERGE, ARGMAX.LOCAL.
  Dependences: per-position records read / write their position's copy of every VM region (VM intervals shifted per
  position, region names suffixed); shared records the union; HBM KV ring writes stay unshifted so every position's
  attention waits for all the block's KV appends of that layer (causal superset).  Wait masks rebuilt.
Attention: option A = the immutable ATT table price (records on ATT); option B (CURRENT die: attention on the SM
engines) = the MEASURED SM attention component spans (results/hbm_sm_attention_1015/b_measured_model.json per-record
exposed / prefetched cycles) executed on the SM unit (they queue with the matvecs).
Sensitivity: the e2e_calibration partial measured unit service ratios (scale_dma_full_bw), as the AR sensitivity.

    python3 -m hgi_sim.ds_mtp_verify --out REC.json [--draft SIM.json]          (from tools/)
"""
from __future__ import annotations

import argparse
import copy
import datetime
import hashlib
import json
import math
import re
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

from hgi_sim import timing as T  # noqa: E402
from hgi_sim import ds_native_timing as DT  # noqa: E402
from hgi_sim.perf import coll_cycles  # noqa: E402

PROGRAM = ROOT / "results/arch/hgi_programs_20261010/inputs/ds_rank0_program.json"
RUN = ROOT / "results/arch/hgi_programs_20261010/inputs/ds_native_1M_run.json"
CALIB = ROOT / "results/arch/hgi_sim_20261009/e2e_calibration.json"
BMODEL = ROOT / "results/hbm_sm_attention_1015/b_measured_model.json"
CLK = 1.2e9
VM_OFF = 1 << 24            # per-position copy of a VM region (dependence bookkeeping only; see VM gap in the record)
SLOT_OFF = 1 << 28          # extra union expert slots
TAU = 4.159                 # DS ROM basis: DSpark gamma 5, owner 6-class blend (blend_owner6.json)
GAMMA = 5
UNION = 23.9                # measured greedy-continuation union of 6 positions' top-6 (proxy, held)

EXPERT_RE = re.compile(r"^expert slot (\d+) (w[123])")
GATHER_RE = re.compile(r"expert_intermediate_gather\.s(\d+)")


def load():
    d, recs = DT.load(PROGRAM)
    recs = T.rebuild_waits(recs)
    rg = {}
    for x in json.loads(RUN.read_text())["results"]:
        for s_ in x.get("row_gather") or []:
            rg[x["layer"]] = s_
    DT.apply_dyn_counts(recs, rg)
    cf = DT.NativeCost(d["ops"], recs, row_gather=rg)
    return d, recs, cf


def att_T(r):
    """the attention record's selection size (640 = window + compressed top-k, 128 = window only)"""
    return r.desc["O"].n if r.op == "QK" else r.desc["A"].n


def classify(r):
    """'shared' | 'pos' | ('expert', slot) | ('egather', slot)"""
    u, op, tag = r.unit, r.op, r.tag or ""
    m = EXPERT_RE.match(tag)
    if u == "SM" and m:
        k = int(m.group(1))
        return ("expert", k) if k < 6 else "shared"
    if u == "SM":
        return "shared"
    if u == "COLL":
        g = GATHER_RE.search(tag)
        if op == "ALL_GATHER" and g:
            k = int(g.group(1))
            return ("egather", k) if k < 6 else "shared"
        if op in ("ALL_GATHER", "GROUP_REDUCE_MCAST") and not ("kv" in tag and "gather" in tag and "slot" in tag):
            return "shared"
        return "pos"
    if u == "SU":
        return "pos" if "I" in r.desc else "shared"
    if u == "DMA":
        if op == "FENCE":
            return "shared"
        if op == "LOAD":
            a = r.desc["A"]
            if a.space == "HBM" and not a.indexed and a.dyn_sel == 0 and "rope" not in (r.tag or ""):
                return "shared"
        return "pos"
    if u == "CTL":
        return "shared"
    return "pos"          # ATT, IDX, FUSED, HC, ARGMAX


class Rec:
    pass


def shift(iv, k):
    return (iv[0], iv[1] + k, iv[2] + k) if iv[0] == "VM" else iv


# ---- multi-position (P-row) records: the H-MTP2 design (2026-10-15) ---------------------------------------------------
# ISA form (no new opcode): a per-position record carries R = P rows; every descriptor with m = R steps by its stride
# per row (the per-position copies of a VM region), a descriptor with m = 1 is broadcast to every row (gains, weights,
# tables); the record retires when the last row's last write is visible.  Cost of a P-row record = c1 + (P - 1) II:
# c1 = the single-row record (its price / measured cost), II = the per-row initiation interval of the binding resource
# AFTER the hardware change (the latency, fixed and broadcast parts are paid once).  Two bases: II_price (the price
# table's own structure), II_meas (the measured RTL structure; None = ratio x II_price).
FCOLL = 108.6 + 377.6e-9 * CLK + 0.15e-6 * CLK      # perf.coll_cycles fixed part (endpoint + crossing + tail), 741.7
HBM_RATIO = 136 / 98.96                              # SM line 136 B at 1 line/cycle vs the SM's 98.96 B/cycle HBM share
SK_PRICE = 0.52778 * 1200                            # Sinkhorn node of the HC_MIX price (ot_hdc_sinkhorn 41 clocks)
HCP_II = (1578 - 328) / 5                            # HCP RTL spec W256 measured x1 328 / x6 (MTP verify) 1,578 cycles
ROW_FAMILIES = ("FUSED.PRE", "FUSED.POST", "FUSED.QDQ", "HC", "ATT", "COLL", "IDX.TOPK", "IDX.INDEX", "SU", "DMA",
                "ARGMAX")


def row_family(r):
    u, op = r.unit, r.op
    if u == "FUSED":
        return {"HC_PRE_NORM": "FUSED.PRE", "HC_POST": "FUSED.POST"}.get(op, "FUSED.QDQ")
    if u == "IDX":
        return "IDX.TOPK" if op == "TOPK" else "IDX.INDEX"
    return u


def row_ii(r, c1, dyn, L, sk_rep=3):
    """(II_price, II_meas | None, basis) of a per-position record as a P-row record (see the block comment)."""
    fam = row_family(r)
    if fam == "FUSED.PRE":
        # price: SU chain 20,480 + 5,120 words at M256 (100 beats) | actquant 32 / cycle on 5,120 (160): 160 binds.
        # LL engine: each of the 32 lanes reads 4 h sectors x 20 (80 VM-bank reads a row; gain kept, writes on W port)
        return 160.0, 80.0, "price: actquant 5,120 / 32; LL: 80 lane reads a row"
    if fam == "FUSED.POST":
        return 100.0, 100.0, "SU chain 25,600 words / 256; LL: 5 reads x 20 sectors a lane"
    if fam == "FUSED.QDQ":
        n = r.desc["A"].n
        return float(math.ceil(n / 32)), float(math.ceil(n / 32)), "quantiser 32 / cycle"
    if fam == "HC":
        return max(HCP_II, SK_PRICE / sk_rep), None, f"HCP x6 measured II {HCP_II:.0f}; Sinkhorn {SK_PRICE:.0f} / {sk_rep} units"
    if fam == "COLL":
        fixed = FCOLL + (T.first_access() if r.op == "ROW_GATHER" else 0.0)
        return max(c1 - fixed, 1.0), None, "collective fixed part paid once (one message train of P payloads)"
    if fam == "IDX.TOPK":
        return 47.0, 47.0, "router top-6 RTL 47 cycles a row (SU route chain 2 beats)"
    if fam == "IDX.INDEX":
        return c1 * 152.0 / 658.9, None, "key stream shared; array ingest 126.7 ns (152 cyc) a query of the 658.9 frame"
    if fam == "SU":
        r2 = copy.copy(r)
        r2.desc = {k: copy.copy(v) for k, v in r.desc.items()}
        for v in r2.desc.values():
            v.m = v.m * 2
        return max(T.su_cost(r2, dyn, L)[0] - T.su_cost(r, dyn, L)[0], 1.0), None, "SU nv x P, depth once"
    if fam == "DMA":
        return max(c1 - T.first_access(), 2.0), None, "first access once; row bytes at full bandwidth"
    if fam == "ARGMAX":
        return 6.0, None, "1,347-row shard / 256 lanes"
    return c1, None, "no P-row form"


SWAP_IN, SWAP_OUT = 335.9, 241.0   # ds_mtp_kernels column swap launch S2 cycles (STRIPE4 h + PRE, results/rtl/hgi_e2e_mtp_20261010)


def compile_verify(recs, cf, P, sm_mode="pport", union=UNION, att="A", bmodel=None, swap=False, pos_scale=None,
                   rows=(), sm_k=None, att_k=None, bcomp=None, sk_rep=3):
    """swap: the P columns' residual h (20,480 words + PRE) do NOT all fit the 2^18-word VM (the AR map ends at
    ~261.7k words): each layer swaps every column in from / out to the HBM column store (ds_mtp_kernels' swap bodies,
    DMA) -- the as-built form; swap=False: VM-resident columns (needs VM growth).  pos_scale: {unit: factor} on the
    per-position records' cost (binding-unit sensitivity).  rows: the ROW_FAMILIES emitted as ONE P-row record (cost
    c1 + (P - 1) II, row_ii); sm_mode "slots": the SM carries sm_k MAC slot sets (one HBM read of a weight line serves
    sm_k positions a pass, ceil(P / sm_k) passes, never faster than the HBM share); att_k: SM attention query slots
    (option B, "ATT" in rows: fixed spans once, the measured component span bcomp x ceil(P / att_k))."""
    """-> (records, notes): the verify(P) record stream; every record carries .fp (reads, writes intervals) and
    .price(scale) (its cost)."""
    dyn = T.Dyn(DT.POS)
    U = max(6, int(round(union))) if P > 1 else 6
    out = []
    stats = dict(shared=0, per_position=0, expert_slots=U, union_records=0)

    def emit(r, poss, base, extra_shift=0, unit=None, cost=None, kind=""):
        c = copy.copy(r)
        rd, wr = T.footprint(r, dyn, r.layer if isinstance(r.layer, int) else 0)
        c.fp = ([shift(iv, p * VM_OFF + extra_shift) for p in poss for iv in rd],
                [shift(iv, p * VM_OFF + extra_shift) for p in poss for iv in wr])
        sfx = (lambda nm, p: f"{nm}@{p}" + (f"#{extra_shift}" if extra_shift else ""))
        c.reads = [sfx(nm, p) for p in poss for nm in getattr(r, "reads", ())]
        c.writes = [sfx(nm, p) for p in poss for nm in getattr(r, "writes", ())]
        c.implicit = ()
        c.base_cost = cost if cost is not None else base
        if pos_scale and len(poss) == 1 and P > 1:
            c.base_cost *= pos_scale.get(unit or r.unit, 1.0)
        c.orig_op = f"{r.unit}.{r.op}"
        c.mtp_kind = kind
        c.npos = len(poss)
        c.ii = None
        if unit:
            c.unit = unit
        out.append(c)
        return c

    allp = list(range(P))
    hrec = next(r for r in recs if r.unit == "FUSED" and r.op == "HC_PRE_NORM")
    h_iv = T.footprint(hrec, dyn, 0)[0]          # the residual h + PRE intervals (HC pre-norm reads them)
    seg_key = None

    def swaps(kind, cyc, layer):
        for p in allp:
            c = copy.copy(hrec)
            c.layer = layer
            c.unit, c.op, c.tag, c.sut = "DMA", "LOAD" if kind == "in" else "STORE", f"column swap {kind}", None
            ivs = [shift(iv, p * VM_OFF) for iv in h_iv]
            c.fp = ([], ivs) if kind == "in" else (ivs, [])
            c.reads = [] if kind == "in" else [f"{nm}@{p}" for nm in hrec.reads]
            c.writes = [f"{nm}@{p}" for nm in hrec.reads] if kind == "in" else []
            c.implicit, c.base_cost, c.orig_op, c.mtp_kind, c.npos = (), cyc, "DMA.SWAP", "swap", 1
            out.append(c)
    for r in recs:
        if r.unit == "CTL" and r.op == "END":
            continue
        k_ = r.layer if isinstance(r.layer, int) and r.layer < 40 else "head"
        if swap and P > 1 and k_ != seg_key:
            if seg_key is not None:
                swaps("out", SWAP_OUT, seg_key)
            swaps("in", SWAP_IN, k_)
            seg_key = k_
        L = r.layer if isinstance(r.layer, int) else 0
        base = cf(r, dyn, L)[0]
        cls = classify(r)
        if r.unit == "ATT":
            T_ = att_T(r)
            if "ATT" in rows and P > 1 and att != "A":
                c_b = bmodel[str(T_)][r.op.lower()]
                comp = bcomp[str(T_)][r.op.lower()]
                k_ = att_k or 1
                emit(r, allp, base, unit="SM", cost=c_b + comp * (math.ceil(P / k_) - 1), kind=f"att_B{T_}_rows")
                stats["shared"] += 1
                continue
            if att == "A":
                for p in allp:
                    emit(r, [p], base, kind="att_A")
            else:
                c_b = bmodel[str(T_)][r.op.lower()]
                for p in allp:
                    emit(r, [p], base, unit="SM", cost=c_b, kind=f"att_B{T_}")
            stats["per_position"] += P
            continue
        if cls == "shared":
            if r.unit == "SM" and sm_mode == "serial" and P > 1:
                for p in allp:
                    emit(r, [p], base, kind="sm_serial")
                stats["per_position"] += P
                continue
            c = base
            if r.unit == "SM" and sm_mode == "slots" and P > 1:
                c = base * max(1.0, math.ceil(P / sm_k) / HBM_RATIO)
            if r.unit == "COLL" and P > 1:
                nb = 4 * r.desc["A"].n
                c = base * coll_cycles(r.op, P * nb, 96)[0] / coll_cycles(r.op, nb, 96)[0]
            elif r.unit == "SU" and P > 1:
                r2 = copy.copy(r)
                r2.desc = {k: copy.copy(v) for k, v in r.desc.items()}
                for v in r2.desc.values():
                    v.m = v.m * P
                c = base * T.su_cost(r2, dyn, L)[0] / T.su_cost(r, dyn, L)[0]
            emit(r, allp, base, cost=c, kind="shared")
            stats["shared"] += 1
            continue
        if isinstance(cls, tuple):
            what, k = cls
            if sm_mode == "serial" and P > 1 and what == "expert":
                # as built: every position runs its own 6 routed experts (no slot port, no union read sharing)
                for p in allp:
                    emit(r, [p], base, kind="expert_serial")
                stats["per_position"] += P
                continue
            for j in range(k, U, 6):                   # union slots j = k, k + 6, ...: P_e = 6 P / U positions each
                pe = 6 * P / U
                c = base
                if what == "egather" and P > 1:
                    nb = 4 * r.desc["A"].n
                    c = base * coll_cycles(r.op, int(round(pe * nb)), 96)[0] / coll_cycles(r.op, nb, 96)[0]
                if what == "expert" and sm_mode == "slots" and P > 1:
                    c = base * max(1.0, math.ceil(math.ceil(pe) / sm_k) / HBM_RATIO)
                emit(r, allp, base, extra_shift=(j // 6) * SLOT_OFF, cost=c, kind=what)
            stats["shared"] += len(range(k, U, 6))
            continue
        # per position
        if P > 1 and row_family(r) in rows:
            iip, iim, _ = row_ii(r, base, dyn, L, sk_rep=sk_rep)
            c = emit(r, allp, base, cost=base + (P - 1) * iip, kind="rows")
            c.ii, c.ii_meas, c.c1 = iip, iim, base
            stats["shared"] += 1
            if r.unit == "IDX" and r.op == "TOPK" and (r.tag or "").startswith("route.top6") and sm_mode != "serial":
                emit(r, allp, base, kind="expert_union")
                stats["union_records"] += 1
            continue
        for p in allp:
            emit(r, [p], base, kind="pos")
        stats["per_position"] += P
        if r.unit == "IDX" and r.op == "TOPK" and (r.tag or "").startswith("route.top6") and P > 1 and sm_mode != "serial":
            emit(r, allp, base, kind="expert_union")       # the per-die union of the P positions' top-6 (ISA gap)
            stats["union_records"] += 1
    end = [r for r in recs if r.unit == "CTL" and r.op == "END"]
    for r in end:
        c = copy.copy(r)
        c.fp, c.base_cost, c.orig_op, c.mtp_kind, c.npos = ([], []), 1.0, "CTL.END", "end", P
        c.implicit = ()
        out.append(c)
    out = T.rebuild_waits(out)
    return out, stats


_FP = T.footprint


def _footprint(r, dyn, L):
    fp = getattr(r, "fp", None)
    return fp if fp is not None else _FP(r, dyn, L)


def cost_fn(scale=None):
    k = scale or {}

    def cf(r, dyn, L):
        c = r.base_cost
        if getattr(r, "ii", None) is not None and k:
            q = k.get(r.orig_op, 1.0)
            iim = r.ii_meas if (r.ii_meas is not None and r.orig_op in k) else q * r.ii
            c = q * r.c1 + (r.npos - 1) * iim
        elif not r.mtp_kind.startswith("att_B"):
            c *= k.get(r.orig_op, 1.0)
        return c, "mtp_verify", f"{r.orig_op} {r.mtp_kind} x{r.npos}"
    return cf


def segments(recs):
    """the program cut at layer boundaries (program order): the S2 schedule's exact-interval dependence scan is
    quadratic in records, so a P = 6 token (~20k records) is scheduled one layer segment at a time and the segments
    are summed (no overlap across a layer boundary: conservative; the AR token is timed the same way AND whole, the
    difference is reported as the segmentation charge)"""
    segs, cur, key = [], [], None
    for r in recs:
        if r.unit == "CTL" and r.op == "END":
            continue
        k = r.layer if isinstance(r.layer, int) and r.layer < 40 else "head"
        if cur and k != key:
            segs.append((key, cur))
            cur = []
        key = k
        cur.append(r)
    if cur:
        segs.append((key, cur))
    return segs


def run(recs, scale=None, whole=False):
    end = [r for r in recs if r.unit == "CTL" and r.op == "END"][:1]
    T.footprint = _footprint
    try:
        if whole:
            s = T.schedule(recs, DT.POS, "S2", cost_fn=cost_fn(scale))
            busy = {u: round(v["busy"], 1) for u, v in s["per_unit"].items()}
            return dict(cycles=round(s["total_cycles"], 1), records=len(recs), unit_busy=busy, timing="whole token")
        tot, busy, per = 0.0, {}, {}
        for key, seg in segments(recs):
            seg = T.rebuild_waits(seg + end)
            s = T.schedule(seg, DT.POS, "S2", cost_fn=cost_fn(scale))
            tot += s["total_cycles"]
            per[str(key)] = round(s["total_cycles"], 1)
            for u, v in s["per_unit"].items():
                busy[u] = busy.get(u, 0.0) + v["busy"]
    finally:
        T.footprint = _FP
    return dict(cycles=round(tot, 1), records=len(recs), unit_busy={u: round(v, 1) for u, v in busy.items()},
                per_segment=per, timing="per layer segment, summed")


_CTX = {}


def _job(job):
    """one schedule of the matrix (process pool worker)"""
    name, kw, scale = job
    if "recs" not in _CTX:
        _CTX["d"], _CTX["recs"], _CTX["cf"] = load()
    prog, st = compile_verify(_CTX["recs"], _CTX["cf"], **kw)
    r = run(prog, scale)
    r["compile"] = st
    r.pop("per_segment", None)
    return name, r


def draft_terms(sim, P):
    """the DSpark draft + seed of one step from a ds_mtp_kernels sim record priced at 1M (launches.json beside it):
    SEED (P columns), DSTAGE x 3 (demb, dsa, dsb + the block rows' swaps), DHEAD (5 rows), MARKOV x gamma, and the
    verify columns' main-hidden stores of layers 37..39 (the layer bodies' extra SU records over the replay body)."""
    L = json.loads((sim.parent / "launches.json").read_text())
    # the step = the launches after the prefill's SEED: draft (anchor 0) ... verify ... SEED(P)
    i0 = next(i for i, x in enumerate(L) if x["kind"] == "seed")          # prefill seed (1 column)
    draft = [x for x in L[i0 + 1:] if x["kind"] in ("demb", "dsa", "dsb", "dhead", "markov")
             or (x["kind"] in ("swapin", "swapout") and x["token"] >= 8)]
    seeds = [x for x in L[i0 + 1:] if x["kind"] == "seed"]
    lay = {x["Lp"]: x["s2_cycles"] for x in L if x["kind"] == "layer" and x["Lp"] in (1, 37, 38, 39)}
    mh = sum(lay[k] - lay[1] for k in (37, 38, 39)) * P
    by = {}
    for x in draft:
        by[x["kind"]] = by.get(x["kind"], 0.0) + x["s2_cycles"]
    return dict(draft_cycles=round(sum(by.values()), 1), draft_by_kind={k: round(v, 1) for k, v in by.items()},
                seed_cycles=round(sum(x["s2_cycles"] for x in seeds[-P:]), 1),
                seed_columns=len(seeds[-P:]), mh_store_cycles=round(mh, 1),
                note="row-serial DSpark draft as lowered (5 block rows one at a time per stage, column swaps), priced "
                     "at the sim's --price-pos")


CTL_CMD = 16                 # dspark ctl command round trip budget MD-1 (closed ot_dshbm_dspark_ctl / accept_a0)


def compose(rec, P):
    """one DSpark step = verify(P) + draft (3 stages x 5 rows, dhead, gamma Markov) + seed(P columns) + the verify
    columns' main-hidden stores (L37..39) + the control plane's commands (40 VLAYER + VHEAD + SEED + 3 DSTAGE + DHEAD +
    gamma MARKOV, MD-1 budget each); tok/s = tau x clock / step.  AR = the same program's P = 1 token (same segmented
    timing).  The sensitivity rows scale the draft + seed terms by the AR sensitivity / fixed ratio (the sim prices
    those kernels on the fixed tables only)."""
    runs, tau, gamma = rec["runs"], rec["tau"], rec["gamma"]
    ncmd = 40 + 1 + 1 + 3 + 1 + gamma
    table = []
    for key, r in runs.items():
        f = key.split("|")
        if f[1] == "AR" or len(f) > 5:
            continue
        att, _, sm, swap, sc = f
        ar = runs[f"{att}|AR|{sc}"]["cycles"]
        dk = "option B" if att.startswith("B") else "ATT tabl"
        d = rec["draft"].get(dk)
        if not d:
            continue
        k = ar / runs[f"{att}|AR|fixed"]["cycles"] if sc != "fixed" else 1.0
        extra = (d["draft_cycles"] + d["seed_cycles"] + d["mh_store_cycles"]) * k + ncmd * CTL_CMD
        step = r["cycles"] + extra
        table.append(dict(case=key, attention=att, sm=sm, vm=swap, prices=sc, verify_cycles=r["cycles"],
                          draft_cycles=round(d["draft_cycles"] * k, 1), seed_cycles=round(d["seed_cycles"] * k, 1),
                          mh_store_cycles=round(d["mh_store_cycles"] * k, 1), control_cycles=ncmd * CTL_CMD,
                          step_cycles=round(step, 1), step_us=round(step / CLK * 1e6, 2),
                          mtp_tok_s=round(tau * CLK / step, 1), ar_cycles=ar, ar_tok_s=round(CLK / ar, 1),
                          mtp_over_ar=round(tau * ar / step, 3)))
    return dict(rule=compose.__doc__, commands_a_step=ncmd, table=table)


def main():
    import multiprocessing as mp
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path)
    ap.add_argument("--draft", type=Path, nargs="*", default=[],
                    help="ds_mtp_kernels sim.json priced at 1M (--price-pos), one per attention option: A then B")
    ap.add_argument("--gamma", type=int, default=GAMMA)
    ap.add_argument("--tau", type=float, default=TAU)
    ap.add_argument("--jobs", type=int, default=8)
    a = ap.parse_args()
    calib = json.loads(CALIB.read_text())["result"]["sensitivity"]["ds_1M"]
    meas = set(calib["calibration_coverage"]["measured_ops"])
    # the partial measured-unit sensitivity: the calibration's DMA-full-bandwidth scale restricted to the ops its
    # coverage grades MEASURED (HC.HC_MIX / HC_MIX_ROWS / QDQ_FP4 ratios come from replay stubs in the cad18 vehicle
    # and are not in measured_ops; on this program HC.HC_MIX is already the measured HCP RTL span + SU + Sinkhorn)
    sens = {u: x for u, x in calib["scale_dma_full_bw"].items() if u in meas}
    scales = dict(fixed=None, sensitivity=sens)
    bm = json.loads(BMODEL.read_text())
    bvar = dict(B_exposed={T_: dict(qk=v["qk"], pv=v["pv"]) for T_, v in bm["exposed"]["per_record"].items()},
                B_prefetch={T_: dict(qk=v["qk"], pv=v["pv"]) for T_, v in bm["prefetch"]["per_record"].items()})
    P = a.gamma + 1
    jobs = []
    for att in ("A", "B_exposed", "B_prefetch"):
        ak = dict(att="A" if att == "A" else "B", bmodel=bvar.get(att))
        for sc, k in scales.items():
            jobs.append((f"{att}|AR|{sc}", dict(P=1, **ak), k))
            for sm_mode in ("pport", "serial"):
                for swap in (True, False):
                    jobs.append((f"{att}|verify{P}|{sm_mode}|{'swap' if swap else 'vmres'}|{sc}",
                                 dict(P=P, sm_mode=sm_mode, swap=swap, **ak), k))
    ak = dict(att="B", bmodel=bvar["B_exposed"])
    jobs.append((f"B_exposed|verify{P}|pport|swap|fixed|U{6 * P}", dict(P=P, sm_mode="pport", swap=True, union=6 * P, **ak),
                 None))
    for u in ("FUSED", "HC", "COLL", "IDX", "SM", "SU", "DMA"):
        jobs.append((f"B_exposed|verify{P}|pport|swap|fixed|batch_{u}", dict(P=P, sm_mode="pport", swap=True,
                     pos_scale={u: 1.0 / P}, **ak), None))
    with mp.Pool(a.jobs) as pool:
        res = dict(pool.map(_job, jobs))
    ar_whole = run(compile_verify(*load()[1:], 1)[0], whole=True)["cycles"]
    rec = dict(schema="opentallas.hgi_sim.ds_mtp_verify.v1",
               generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               position=DT.POS, gamma=a.gamma, P=P, tau=a.tau, union=UNION, clock_hz=CLK,
               program=str(PROGRAM.relative_to(ROOT)), program_sha256=hashlib.sha256(PROGRAM.read_bytes()).hexdigest(),
               b_model=str(BMODEL.relative_to(ROOT)), calibration=str(CALIB.relative_to(ROOT)),
               ar_whole_token_fixed_A=ar_whole, sensitivity_scale=sens, runs=res)
    rec["draft"] = {}
    for dpath in a.draft:
        sim = json.loads(dpath.read_text())
        rec["draft"][sim.get("att_pricing", "?")[:8]] = dict(source=str(dpath), verdict=sim["verdict"],
                                                          price_pos=sim.get("price_pos"), **draft_terms(dpath, P))
    rec["steps"] = compose(rec, P)
    print(json.dumps({k: v["cycles"] for k, v in res.items()}, indent=1))
    print(json.dumps(rec["steps"]["table"], indent=1))
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(rec, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
