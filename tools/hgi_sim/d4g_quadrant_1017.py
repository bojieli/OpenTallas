#!/usr/bin/env python3
"""HBM-B-RTL3 (10-17): d4g plan (b) compiler pass -- quadrant-local placement + DMA + fixed static schedule -- and the
re-price of DS AR / DS MTP (3,500 design point) / Qwen3-8B AR on the hgi price model (plan_study_price_1017 machinery).

D4G GEOMETRY (results/arch/hbm_plan_study_1017/plan_b_inner/compact.P.json):
  16 SM = 4 quadrants x 4 SM (SW, SE, NW, NE; ring qid 0 SW, 1 SE, 2 NW, 3 NE, CW order 0 -> 1 -> 3 -> 2).
  2 HBM stacks x 8 PCs: south stack pc_SW0..7 (PHY phy_SW), north stack pc_NW0..7 (phy_NW).
  Lever 1: quadrant SW = pc_SW0..3, SE = pc_SW4..7, NW = pc_NW0..3, NE = pc_NW4..7 (the PCs directly in front of it).

(A) PLACEMENT + DMA (the compiler pass; `place_programme`):
  W1  SM.MATVEC row-split matrices: the die's m rows are dealt in blocks of R = ceil(m / 16) to SM 0..15 (the timing
      model's per-SM floor rule); SM j's block lives in quadrant j // 4's 4 PCs, PC-interleaved inside the quadrant.
      Checked: every SM reads only its own quadrant's PCs; the busiest quadrant's bytes / (4 x per-SM share) equals the
      busiest SM's bytes / share (the per-SM floor already priced), so lever 1 costs 0 cycles when this holds.
  W2  head-aligned work (wq_b of the die's head, wo_a K-split) and attention KV: token blocks of the head are dealt to
      the 16 SMs the same way; each SM's KV lines (KV_DESC + SM_HBM) and KVWB_DS appends go to its quadrant's PCs.
  D1  DMA.LOAD whose VM consumer is quadrant-sliced (HC rows -> the quadrant HC engine's hidden slice; KV / row gather ->
      the token-owning SMs): split 4 ways, quadrant q loads its share on its own 4 PCs into its own 8 banks (same
      stream time as the die-wide load: 1/4 the bytes at 1/4 the bandwidth).
  D2  DMA.LOAD of a table every quadrant reads (norm gains, rope / sink tables, route bias, engram codes/scales):
      REPLICATED: the table image is placed once per quadrant (4 copies, capacity counted) and each quadrant loads its
      own copy: stream part x 4 (1/4 the bandwidth), first access unchanged.
  C1  COLL.* results that an SM-side consumer reads in every quadrant (gathers of qa / kvraw / iq / gsc / cmp / iwr,
      the o-group reduce-mcast, the 7 expert-intermediate gathers): each quadrant COLL engine writes ONLY its 8 banks,
      so its quarter is replicated by the on-die ALL-GATHER on the COLL ring (rtl ot_hgi_coll_ring_ag, GATHER kind 3).
  C2  COLL.* results whose consumer is quadrant-sliced (attn_out y / ffn_out yf -> HC_POST of the quadrant HC engine's
      hidden slice): the sender dies address quadrant q's endpoint with slice q (switch multicast pattern only) -> no
      ring traffic, no added cycles.
  C3  ROW_GATHER rows go to the token-owning quadrant's endpoint (W2) -> no ring traffic.
  C4  merges (TOPK_MERGE / ARGMAX_MERGE) land in the quadrant that owns the consumer -> one XQ tree crossing.

(B) FIXED STATIC SCHEDULE ADDERS (cycles at 1.2 GHz, added to the record's unit cost; the same S2 schedule is re-run, so
    latency is exposed only where the programme is serially dependent):
  AG   on-die all-gather of a C1 record, B = result bytes in VM words (4 B), F = ceil(B / 4 / 32) flits a quadrant:
       ring schedule MODE 0 (bench tb_hgi_coll_ring_ag: even flits CW / odd CCW, ttl 3): 1.5 F + 3 hops, hop = 2 edges
       + r relay stages (r = COLL_RING stages of the plan).  Measured on the RTL at r = 0: F 224 -> 336 inject edges +
       6 = 342..; F 112 -> 168 + 6.  Cut-through (nominal): the ring forwards a slice as it lands, so the exposed part
       is max(0, 1.5 F - D) + 3 hop, D = the off-die delivery stream of that record ((G-1) f / lanes, ds_die_split).
       MODE 1 (both directions, ttl 2 + 1): 2 F + 2 hops; the compiler takes the cheaper ring schedule per record.
       Alternative M (compiler choice): the switch multicasts to all 4 quadrant endpoints: + 3 D (delivery x 4, one lane
       a quadrant).  The compiler takes min(AG, M) per record.
  XQT  cross-quadrant trees (plan R3, XQ lanes), one crossing = 1 + XQ stages (XQ = COLL_RING stages of the plan):
       SU.VOP with a reduction (sut.red: RMS / softmax scalars): SU 64-b scalar tree up + down = 2 crossings;
       HC.HC_MIX / FUSED.HC_PRE_NORM: hcx_root 1,024-b partial-sum tree up + down = 2 crossings (HC_POST is
       element-wise on the slice: 0); IDX.INDEX / IDX.TOPK: quadrant lists -> selector merge = 1; ARGMAX.LOCAL = 2;
       COLL TOPK_MERGE / ARGMAX_MERGE (C4) = 1.
  SU   SU programme slice pslice r4/c5: start advance DEPTH + 4 -> +4 a SU-executed record (SU.VOP, FUSED non-QDQ/HC).
  SFUD SFU programme store r10 cluster relays: D 4 -> 5 -> +1 a SFU-using record (SFU.*, SU.VOP with sut.sfu).
  SFUC SFU chains R11 -> R14 (+3 edges each way of the LG VM round trip) -> +6 a SFU-using record.
  BD   broadcast depth (lane model, equal-age forks: every sink sees the fork's full depth, not the bit-weighted mean):
       plan_b_inner deep list x the run9 fork calibration 1.204: xl_<Q>_ctl x data fork 40 -> 48.2 stages (SM_X data
       leg; request leg keeps the class mean) and vmks fill fork 44 -> 53.0 (HBM_VM).
       nominal: the x-data fork runs in parallel with the weight fetch leg (2 SM_HBM [+ KV_DESC] + the HBM first
       access 104), so an SM record pays only max(0, SM_X + 48.2 - that leg); a DMA record pays 53.0 - HBM_VM.
       upper ("plan_b_bd" stages): the per-class table is overridden, SM_X = (mean + 48.2) / 2 (2 crossings:
       request + data), HBM_VM = max(mean, 53.0), on the ds_relay_latency absolute-leg rule (no first access).
  RTL1/RTL2 latencies (SU scalar tree, HC partial tree, IDX quarters, VM client side) enter through LEDGER entries
  (results/arch/hbm_d4g_price_1017/latency_ledger.json): a 'measured' entry sets knob = cycles (bench-measured edges)
  + xq_crossings x COLL_RING (die relay stages the bench did not have).  10-17 23:59 measured: su_tree 28 (RTL1
  RF_TREE_UP/DN 14+14), hc_tree 28 + 2 XQ (RTL2 HC split RAW0 165 vs 137 + XRD + XRU), idx_merge 8 + 1 XQ (RTL2 IDX
  quad: first TX / every TX flit +8 incl. the +2 calendar start).

    PYTHONPATH=tools python3 -m hgi_sim.d4g_quadrant_1017 --out results/arch/hbm_d4g_price_1017/price.json
"""
from __future__ import annotations

import argparse
import copy
import datetime
import json
import math
import multiprocessing as mp
import re
from pathlib import Path

from hgi_sim import plan_study_price_1017 as PS
from hgi_sim import ds_switch_sens as W
from hgi_sim import ds_die_split as S
from hgi_sim import ds_relay_latency as RL
from hgi_sim import ds_mtp_verify as V
from hgi_sim import timing as T

CLK = S.CLK
ROOT = S.ROOT
NQ, SM_PER_Q, NSM = 4, 4, 16
QNAME = ["SW", "SE", "NW", "NE"]
QPCS = {"SW": [f"pc_SW{i}" for i in range(4)], "SE": [f"pc_SW{i}" for i in range(4, 8)],
        "NW": [f"pc_NW{i}" for i in range(4)], "NE": [f"pc_NW{i}" for i in range(4, 8)]}
RING_FLIT_B = 32                      # 256-b ring payload
VM_WORD_B = 4
FORK_CAL = 1.204                      # run9 measured / model fork depth (plan study bus calibration)
BD_MODEL = dict(SM_X_data=40, HBM_VM=44)        # plan_b_inner equal-age forks: xl_<Q>_ctl.c_d, vmks fill
LEDGER = ROOT / "results/arch/hbm_d4g_price_1017/latency_ledger.json"

# C2: gathers whose consumer is the quadrant-sliced HC engine (HC_POST) -> slice delivery, no ring
SLICED_GATHERS = ("attn_out_gather", "ffn_out_gather")
# D2: replicated tables (every quadrant reads them)
# QBG (coordinator 0dr addition, 10-18): quantize-before-gather. Gathered tensors whose ONLY consumer is an FP8
# block-dot linear (golden linear_q -> quant_fp8, block 32, UE8M0 exponent) are quantised in the source quadrant by the
# same activation quantiser the SM x-load uses and gathered as E4M3 codes + one exponent byte per 32-block:
#   expert_intermediate_gather.s* : a = silu(g) u -> to_bf16 -> linear_q(w2)          (hdc_golden_v41.expert)
#   o-group (GROUP_REDUCE_MCAST)   : z = to_bf16(grouped wo_a) -> linear_q(wo_b)      (hdc_golden_v41 attention)
#   engram.rows_gather             : decoded rows -> linear_q(engram.wkv)              (hdc_golden_v41.engram_layer)
# Everything else (qa -> q_norm, kvraw -> kv_norm, iq -> FP4 index quant, gsc -> router, cmp, iwr, engram kv) stays
# full precision; Qwen stays full precision.  Bit-exactness: quant_fp8 is per 32-block, so quantising each quadrant
# slice separately equals quantising the whole vector iff every quadrant slice boundary is a multiple of 32
# (qbg_slice_check below; bench tools/hgi_sim/qbg_quant_bench_1018.py against the reference quantizer).
QBG_TAGS = ("expert_intermediate_gather.", "o-group", "engram.rows_gather.")
QBG_BLOCK = 32
REPL_TABLES = ("q_norm.gain", "kv_norm.gain", "route.bias", "kv_rope.table", "attend.sink_table", "route.one",
               "engram.codes", "engram.scales", "engram.wgt", "engram.ids")


# ----------------------------------------------------------------------------------------------------------------
# (A) placement / DMA pass
# ----------------------------------------------------------------------------------------------------------------
def sm_blocks(m):
    """rows of a die's m-row matrix dealt to the 16 SMs in blocks of R = ceil(m / 16): [(sm, r0, r1)]"""
    R = -(-m // NSM)
    return [(j, j * R, min(m, (j + 1) * R)) for j in range(NSM) if j * R < m]


def quadrant_rows(m):
    q = [0] * NQ
    for j, r0, r1 in sm_blocks(m):
        q[j // SM_PER_Q] += r1 - r0
    return q


def classify(r):
    """the d4g placement / delivery class of one record (module doc A)"""
    op = getattr(r, "orig_op", f"{r.unit}.{r.op}")
    tag = r.tag or ""
    if op == "SM.MATVEC":
        return "W2" if S.is_head_sm(tag) else "W1"
    if op.startswith("ATT."):
        return "W2"
    if op == "DMA.KVWB_DS":
        return "W2"
    if op in ("DMA.LOAD", "DMA.SWAP"):
        return "D2" if re.sub(r"\d+$", "", tag.split(" ")[0]) in REPL_TABLES else "D1"
    if r.unit == "COLL":
        if r.op == "ROW_GATHER":
            return "C3"
        if r.op in ("TOPK_MERGE", "ARGMAX_MERGE"):
            return "C4"
        if tag.startswith(SLICED_GATHERS):
            return "C2"
        return "C1"
    return "-"


def coll_bytes(r):
    """(result bytes in VM words, off-die wire bytes) of a COLL record (ds_die_split conventions)"""
    A = r.desc.get("A")
    n = A.n if A is not None else 1
    m = max(1, getattr(A, "m", 1) or 1) if A is not None else 1
    kind = getattr(r, "mtp_kind", "") or ""
    pos = (getattr(r, "npos", 1) or 1) if kind in ("shared", "egather") else 1
    return n * m * VM_WORD_B * pos, n * m * 2 * pos


def place_programme(prog, G1=192, lanes=4):
    """the placement / DMA pass over one compiled programme: class census, per-record checks, replica capacity"""
    cen, checks, repl = {}, dict(sm_records=0, sm_quadrant_local=0, worst_quadrant_over_sm_floor=1.0), {}
    for r in prog:
        c = classify(r)
        cen[c] = cen.get(c, 0) + 1
        if c in ("W1", "W2") and r.unit == "SM":
            b = r.desc["B"]
            m = b.m or 1
            qr = quadrant_rows(m)
            R = -(-m // NSM)
            checks["sm_records"] += 1
            # quadrant q streams its rows on its 4 PCs: time = max_q rows / (4 x per-SM share)
            ratio = (max(qr) / (SM_PER_Q * R)) if R else 1.0
            checks["worst_quadrant_over_sm_floor"] = max(checks["worst_quadrant_over_sm_floor"], ratio)
            checks["sm_quadrant_local"] += 1
        if c == "D2":
            A = r.desc.get("A")
            nb = (A.n * (A.m or 1) * T.ESZ.get(A.fmt, 4)) if A is not None else 0
            k = re.sub(r"\d+$", "", r.tag or "")
            repl[k] = max(repl.get(k, 0), nb)
    return dict(class_census=cen, checks=checks, replicated_tables_bytes=repl,
                replica_capacity_bytes_per_layer=3 * sum(repl.values()))


# ----------------------------------------------------------------------------------------------------------------
# (B) static schedule adders
# ----------------------------------------------------------------------------------------------------------------
_D4G = {}


def ag_cycles(B, r_hop, D=0.0, nominal=True, rings=1):
    """ring all-gather of B bytes (B / 4 a quadrant): min over the two bench-proven ring schedules,
    MODE 0 (one direction a flit, ttl 3: 1.5 F + 3 hops) and MODE 1 (both directions, ttl 2 + 1: 2 F + 2 hops);
    rings = parallel ring instances (the slice is split over them)"""
    F = -(-B // NQ // (RING_FLIT_B * rings))
    hop = 2 + r_hop
    best = None
    for ser, hops in ((math.ceil(1.5 * F), 3), (2 * F, 2)):
        v = (max(0.0, ser - D) if nominal else ser) + hops * hop
        best = v if best is None else min(best, v)
    return best, F


# HBM-COLLQ (10-18): MEASURED gather-master span (rtl ot_hgi_coll_gq, bench tb_hgi_coll_gq, compiler model
# tools/hgi_sim/collq_gather_1018.py, constants results/arch/hbm_die_d4g/collq/collq_schedule.json):
#   launch -> fire 3 edges; fire -> last bank write = 1 + 3 ((K-1) >> 1) + ((K-1) & 1) + 38, K = ceil(F / R), F = the
#   quadrant slice in 256-b flits (QBG: codes + exponent words).  The 38 fixed edges = VM read + quantiser/payload +
#   merge register + ring inject + 3 ring hops (2 edges each, r = 0 in the bench) + publish capture/kq/write; the die
#   adds 3 x COLL_RING relay stages (3 hops).  Opt-in knob ag_collq (cut-through as the ring model: the issue part
#   can overlap the off-die delivery D; the fixed part never does).
COLLQ_FIRE_FROM_LAUNCH = 3
COLLQ_FIXED = 38
# every ISA ring-A command (COLL engine reductions, merges, slice deliveries through the v8x/v8g parent) passes the gather
# master's ring-A MERGE register: +2 edges vs the v5 parent (knob ra_extra on every non-gather COLL record)
COLLQ_RA_EXTRA = 2


def collq_span(F, R):
    """(issue part, fixed part) of the gather-master span in edges for F flits a quadrant over R rings"""
    K = max(1, -(-F // R))
    return 1 + 3 * ((K - 1) >> 1) + ((K - 1) & 1), COLLQ_FIRE_FROM_LAUNCH + COLLQ_FIXED


def qbg_ok(r):
    """the C1 record qualifies for quantize-before-gather (QBG_TAGS) and its quadrant slices are 32-block aligned"""
    tag = r.tag or ""
    if not tag.startswith(QBG_TAGS):
        return False
    A = r.desc.get("A")
    n = A.n if A is not None else 0
    return n > 0 and n % (NQ * QBG_BLOCK) == 0


def qbg_census(prog):
    """AG traffic census of one programme: bytes per C1 tag, the QBG-qualifying fraction and the slice check"""
    rows, tot, ok = {}, 0, 0
    for r in prog:
        if classify(r) != "C1":
            continue
        B, _ = coll_bytes(r)
        A = r.desc.get("A")
        n = A.n if A is not None else 0
        k = re.sub(r"\s.*", "", r.tag or "")
        e = rows.setdefault(k, dict(records=0, bytes=0, n=n, quadrant_slice=n / NQ,
                                    qualifies=bool((r.tag or "").startswith(QBG_TAGS)),
                                    slice_mod32=(n // NQ) % 32 if n % NQ == 0 else None,
                                    slice_mod128=(n // NQ) % 128 if n % NQ == 0 else None))
        e["records"] += 1
        e["bytes"] += B
        tot += B
        ok += B if qbg_ok(r) else 0
    return dict(per_tag=rows, ag_bytes_total=tot, ag_bytes_qbg=ok, qbg_fraction=round(ok / tot, 4) if tot else 0.0,
                qbg_bytes_after=ok // VM_WORD_B + ok // VM_WORD_B // QBG_BLOCK,
                slice_rule="quadrant slice n/4 must be a multiple of the golden act_quant block (32); 128 reported for reference")


def sfu_using(r):
    sut = getattr(r, "sut", None)
    return r.unit == "SFU" or (r.unit == "SU" and isinstance(sut, dict) and sut.get("sfu"))


def su_exec(r):
    op = getattr(r, "orig_op", f"{r.unit}.{r.op}")
    return r.unit == "SU" or (r.unit == "FUSED" and not r.op.startswith(("QDQ", "HC_")) and op != "FUSED.HC_POST")


def d4g_added(r, c, kn):
    """the d4g adders of one record (module doc B); kn = dict(on: set of adder names, xq, r_hop, G1, lanes, nominal)"""
    on = kn["on"]
    op = getattr(r, "orig_op", f"{r.unit}.{r.op}")
    add = 0.0
    xq = 1 + kn["xq"]
    cl = classify(r)
    if "AG" in on and cl == "C1" and c > 0:
        B, wire = coll_bytes(r)
        if kn.get("ag_fp8") and r.op == "ALL_GATHER":
            B = B // VM_WORD_B + B // VM_WORD_B // 32          # FP8 k32 operand + E8M0 scales (opt-in, see doc)
        elif kn.get("ag_qbg") and qbg_ok(r):
            B = B // VM_WORD_B + B // VM_WORD_B // QBG_BLOCK   # QBG: E4M3 codes + 1 exponent byte a 32-block
        f1 = max(1, math.ceil(wire / kn["G1"] / 64))
        D = S.deliver(f1, kn["G1"], kn["lanes"])
        if kn.get("ag_collq"):
            F = -(-B // NQ // RING_FLIT_B)
            ser, fixed = collq_span(F, kn.get("rings", 1))
            ag = (max(0.0, ser - D) if kn["nominal"] else ser) + fixed + 3 * kn["r_hop"]
        else:
            ag, _ = ag_cycles(B, kn["r_hop"], D, kn["nominal"], kn.get("rings", 1))
        add += min(ag, 3 * D) if kn.get("allow_mcast", True) else ag
    if kn.get("ra_extra") and r.unit == "COLL" and cl != "C1" and c > 0:
        add += kn["ra_extra"]
    if "XQT" in on:
        sut = getattr(r, "sut", None)
        if r.unit == "SU" and isinstance(sut, dict) and sut.get("red"):
            add += kn.get("su_tree", 2 * xq)
        elif op in ("HC.HC_MIX", "FUSED.HC_PRE_NORM"):
            add += kn.get("hc_tree", 2 * xq)
        elif op in ("IDX.INDEX", "IDX.TOPK"):
            add += kn.get("idx_merge", xq)
        elif op == "ARGMAX.LOCAL":
            add += 2 * xq
        elif cl == "C4" and c > 0:
            add += xq
    if "BD" in on:
        # broadcast depth, nominal: the SM x-data fork runs in parallel with the weight fetch leg (2 SM_HBM + the HBM
        # first access), so only its excess over that leg is exposed; the VM fill fork (HBM_VM) is serial.
        b = kn["stages"]
        if r.unit in ("SM", "ATT"):
            xe = b["SM_X"] + FORK_CAL * BD_MODEL["SM_X_data"]
            leg = max(2 * b["SM_X"], 2 * b["SM_HBM"] + (b["KV_DESC"] if r.unit == "ATT" else 0.0) + S.first_access())
            add += max(0.0, xe - leg)
        elif r.unit == "DMA" and r.op in ("LOAD", "FENCE", "SWAP"):
            add += max(0.0, FORK_CAL * BD_MODEL["HBM_VM"] - b["HBM_VM"])
    if "D2" in on and cl == "D2":
        fa = S.first_access()
        if c > fa:
            add += (NQ - 1) * (c - fa)
    if "SU" in on and su_exec(r):
        add += kn.get("su_start", 4)
    if "SFUD" in on and sfu_using(r):
        add += kn.get("sfu_d", 1)
    if "SFUC" in on and sfu_using(r):
        add += kn.get("sfu_chain", 6)
    return add


_PREV = V.cost_fn                     # ds_switch_sens wrapper (relay knob + split + switch X)


def cost_fn(scale=None):
    base = _PREV(scale)
    if not _D4G:
        return base

    def cf(r, dyn, L):
        c, g, how = base(r, dyn, L)
        return c + d4g_added(r, c, _D4G), g, how
    return cf


V.cost_fn = cost_fn


def bd_stages(st, plan="plan_b"):
    """plan stages with the broadcast-depth override (BD)"""
    o = dict(st[plan])
    o["SM_X"] = (o["SM_X"] + FORK_CAL * BD_MODEL["SM_X_data"]) / 2
    o["HBM_VM"] = max(o["HBM_VM"], FORK_CAL * BD_MODEL["HBM_VM"])
    return o


def load_ledger():
    try:
        return json.loads(LEDGER.read_text())
    except FileNotFoundError:
        return {}


def knob(on, st, plan="plan_b", nominal=True, ledger=None):
    k = dict(on=set(on), xq=st[plan]["COLL_RING"], r_hop=st[plan]["COLL_RING"], G1=192, lanes=4, nominal=nominal,
             stages=st[plan])
    for e in (ledger or {}).get("entries", []):
        if e.get("status") == "measured" and e.get("knob"):
            # measured RTL edges + die relay crossings of this plan (xq_crossings x COLL_RING stages; 0 in the benches)
            k[e["knob"]] = e["cycles"] + e.get("xq_crossings", 0) * k["xq"]
    return k


def _job(job):
    name, case, var, stages, kn = job
    _D4G.clear()
    if kn:
        _D4G.update(kn)
    return W._job((name, case, var, stages, 377.6, False))


def _qwen(job):
    """Qwen3-8B AR: ds_die_split._qwen_job (relay knob + Qwen split) with the d4g adders on the unit cost"""
    name, var, stages, kn = job
    _D4G.clear()
    if not kn:
        return S._qwen_job((name, var, stages))
    q = var.get("qwen") or {}
    kq = dict(kn, G1=q.get("G1", 8), lanes=q.get("lanes", 4))
    kq.pop("ag_qbg", None)            # Qwen stays full precision (coordinator 0dr)
    kq.pop("ag_fp8", None)
    base = T.cost

    def cost(r, dyn, L, cfg=None):
        c, g, how = base(r, dyn, L, cfg) if cfg is not None else base(r, dyn, L)
        return c + d4g_added(r, c, kq), g, how
    T.cost = cost
    try:
        return S._qwen_job((name, var, stages))
    finally:
        T.cost = base


def _any(job):
    return _qwen(job[1:]) if job[0] == "qwen" else _job(job[1:])


def _census(_):
    S.set_variant(PS.VARIANTS["b"], json.loads((ROOT / "results/arch/hbm_plan_study_1017/stages.json").read_text()))
    prog = RL.compile_case("AR")
    out = place_programme(prog)
    out["qbg_census_AR"] = qbg_census(prog)
    return out


def static_schedule(kn):
    """the fixed static-schedule constants the d4g compiler emits per record class (cycles at 1.2 GHz; the
    programme generators use the same numbers: hbm_idx_static_calendar --score-chain, HC_MIX RAW0, SU UP/DN)"""
    xq = 1 + kn["xq"]
    hop = 2 + kn["r_hop"]
    return {
        "AG_C1_ring_allgather": dict(rule="min(ceil(1.5 F) + 3 hop, 2 F + 2 hop) with cut-through min(.., 3 D multicast)",
                                     hop_edges=hop, F="ceil(B / 4 quadrants / 32 B)",
                                     example_F224=ag_cycles(224 * 4 * 32, kn["r_hop"], 0.0, False)[0]),
        "SU_VOP_reduction_scalar_tree": kn.get("su_tree", 2 * xq),
        "HC_MIX_partial_sum_tree": kn.get("hc_tree", 2 * xq),
        "HC_ingest_event_advance": 2 + kn["xq"],
        "IDX_quarter_merge": kn.get("idx_merge", xq),
        "IDX_score_chain": 14,
        "ARGMAX_LOCAL": 2 * xq, "COLL_TOPK_ARGMAX_MERGE_C4": xq,
        "SU_start_advance": kn.get("su_start", 4), "SFU_store_D": kn.get("sfu_d", 1), "SFU_chain_LG": kn.get("sfu_chain", 6),
        "D2_replicated_table_stream_factor": NQ,
        "placement": "W1/W2 rows dealt in R=ceil(m/16) blocks, SM j in quadrant j//4 on its own 4 PCs (QPCS); "
                     "D1 quadrant-sliced loads split 4 ways; D2 tables replicated x4; C2/C3 slice-addressed, no ring",
        "quadrant_pcs": QPCS,
    }


ADDERS = ["AG", "XQT", "D2", "SU", "SFUD", "SFUC", "BD"]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stages", type=Path, default=ROOT / "results/arch/hbm_plan_study_1017/stages.json")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--jobs", type=int, default=24)
    a = ap.parse_args()
    st = json.loads(a.stages.read_text())
    st["plan_b_bd"] = bd_stages(st)
    led = load_ledger()
    vb = PS.VARIANTS["b"]
    vbd = dict(vb, stages="plan_b_bd")
    variants = {"b_plan": (vb, None)}
    variants["d4g_nominal"] = (vb, knob(ADDERS, st, nominal=True, ledger=led))
    variants["d4g_upper"] = (vbd, dict(knob([x for x in ADDERS if x != "BD"], st, nominal=False, ledger=led),
                                       allow_mcast=False))
    for x in ADDERS:                                 # attribution: one adder alone on top of b_plan
        variants[f"only_{x}"] = (vb, knob([x], st, ledger=led))
    variants["only_BD_upper"] = (vbd, None)
    # compiler / lane options on top of d4g_nominal (not adopted by default)
    variants["opt_2ring"] = (vb, dict(knob(ADDERS, st, ledger=led), rings=2))
    variants["opt_fp8_gather"] = (vb, dict(knob(ADDERS, st, ledger=led), ag_fp8=True))
    variants["opt_2ring_fp8"] = (vb, dict(knob(ADDERS, st, ledger=led), rings=2, ag_fp8=True))
    # coordinator 0dr: two rings ADOPTED (d4g_2ring = the new d4g headline); QBG on top (adopted if bit-exact)
    variants["opt_qbg"] = (vb, dict(knob(ADDERS, st, ledger=led), ag_qbg=True))
    variants["opt_2ring_qbg"] = (vb, dict(knob(ADDERS, st, ledger=led), rings=2, ag_qbg=True))
    variants["d4g_2ring_upper"] = (vbd, dict(knob([x for x in ADDERS if x != "BD"], st, nominal=False, ledger=led),
                                             allow_mcast=False, rings=2))
    variants["d4g_2ring_qbg_upper"] = (vbd, dict(knob([x for x in ADDERS if x != "BD"], st, nominal=False, ledger=led),
                                                 allow_mcast=False, rings=2, ag_qbg=True))
    jobs = [("ds", f"{k}|{case}", case, v, st, kn) for k, (v, kn) in variants.items()
            for case in ("AR", "MTP_design", "draft_design")]
    jobs += [("qwen", f"{k}|qwen", v, st, kn) for k, (v, kn) in variants.items()]
    with mp.Pool(a.jobs) as pool:
        cen = pool.apply_async(_census, (0,))
        res = dict(pool.map(_any, jobs, chunksize=1))
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
    b = table["b_plan"]
    for t in table.values():
        t["d_ar_pct_vs_b_plan"] = round(100 * (t["ar_tok_s"] / b["ar_tok_s"] - 1), 2)
        t["d_mtp_pct_vs_b_plan"] = round(100 * (t["mtp_design_tok_s"] / b["mtp_design_tok_s"] - 1), 2)
        t["d_qwen_pct_vs_b_plan"] = round(100 * (t["qwen_tok_s"] / b["qwen_tok_s"] - 1), 2)
    # AG census: per C1 record the ring all-gather vs multicast choice (AR programme, plan b stages)
    out = dict(schema="opentallas.hbm_d4g_price_1017.v1",
               generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               rule=__doc__, stages_plan_b=st["plan_b"], stages_plan_b_bd=st["plan_b_bd"], ledger=led,
               knob_nominal={k: (sorted(v) if isinstance(v, set) else v) for k, v in variants["d4g_nominal"][1].items()},
               placement=census, table=table, static_schedule=static_schedule(variants["d4g_nominal"][1]),
               d4f_reference=dict(plan_a_ar=1763.0, plan_a_mtp=3022.3, plan_a_qwen=933.6,
                                  note="plan-study (a) d4f price, no d4g adders (results/arch/hbm_plan_study_1017/price.json)"))
    print(json.dumps(dict(table=table, placement=census), indent=1, default=str))
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(out, indent=1, default=str) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
