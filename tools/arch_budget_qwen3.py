#!/usr/bin/env python3
"""Top-down architecture budget of the Qwen3-8B decode core (docs/ARCH_SPEC_QWEN3.md).

    python3 tools/arch_budget_qwen3.py [--out results/arch/qwen3_budget.json]

Requirements first, then per-block specs: this model derives, from the model
graph alone, the per-token WORKLOAD (MACs by op class, bytes by storage level,
elementwise element-ops, reductions, the dependent-stage chain of a layer), the
per-resource ROOFLINE of the two Qwen3-8B designs

* ROM -- the single-reticle Taalas-HC1-class die (N6, 815 mm2) whose compute
  share (146.7 mm2) fixes 8,192 weight-lane groups = 131,072 BF16 MAC lanes;
  weights in ROM; users' KV in HBM stacks on the die's beachfront (user
  decision), the freed SRAM re-budgeted (area_ledger);
* HBM -- the iso-area comparator: one reticle of logic with 6 HBM3E stacks (the
  reticle's beachfront at the 60% edge use of shipping parts: 2 x (26 + 33) mm x
  0.6 / 12 mm per stack = 5.9), weights and KV streamed;

then a BUDGET (each non-binding resource gets a share of the token time) and,
from it, PER-BLOCK REQUIREMENTS: MAC lanes, ROM/HBM read width, KV banks and
bytes a cycle, stream-unit width, reduction-tree depth, the largest exposed
latency a dependent stage may have, buffers, issue rate, argmax.  The GAP table
holds each requirement against the RTL as built, priced by the RTL-calibrated
sequencer model (tools/hdc_timing.simulate, 32,191 model vs 32,196 RTL cycles
on the reduced vehicle) replaying the decode program at the shipped shapes.

Everything here is derived; the only inputs are the model's config.json shapes
(tools/hdc_timing.SHAPES), the reticle split of the analytical study, routed
ASAP7 areas and clocks, and the RTL-calibrated unit latencies.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import hdc_isa as I  # noqa: E402
import hdc_timing as T  # noqa: E402

SCHEMA = "opentallas.arch-budget-qwen3.v1"
OUT = ROOT / "results/arch/qwen3_budget.json"
BASELINE = ROOT / "results/arch/qwen3_baseline_as_built.json"   # as built before the spec work (92f2c723)
MATVEC_PHYS = ROOT / "results/physical_abi3/asap7/hdc/ot_hdc_matvec/physical.json"
STREAM_PHYS = ROOT / "results/physical_abi3/asap7/hdc/ot_hdc_stream/physical.json"

Q = T.SHAPES["qwen3-8b"]
CTX_HEAD = 8192                   # user decision: the design target context
CONTEXTS = (8192, 2048)
KV_FORMATS = {"bf16": 2, "fp8": 1, "int4": 0.5}   # bytes per KV element
KV_FMT_SPEC = "fp8"               # the design point's KV format (a golden change: BF16 today)
CLOCK = [1.0e9]                   # set by evaluate()
W, IL = I.W_LANES, I.INTERLEAVE

# -- the two designs ---------------------------------------------------------------
RETICLE = dict(die_mm2=815.0, node="N6", rom_mm2=261.98, compute_mm2=146.7, sram_mm2=259.62,
               interconnect_mm2=65.2, overhead_mm2=81.5, weight_bits=3.5,
               source="opentallas.roofline.taalas_hc1_anchor on configs/models/qwen3-8b.json "
                      "(tools/decode_critical_path.py qwen3_8b_single_reticle)")
MAC_UM2 = 1071.8171875            # routed ot_hdc_matvec area / 64 lanes (ASAP7, not scaled to N6)
SU_LANE_UM2 = 42443.2             # routed ot_hdc_stream area per element/cycle (ASAP7)
SRAM_BITS_PER_MM2 = 24.07e6       # usable SRAM bits/mm2 (configs/hardware/technology.json)
GROUPS_BUDGET = 7680              # floor(146.7 mm2 x 0.9 / MAC_UM2 / 16): the reticle's lane budget
GROUPS_ROM = 8192                 # the spec: a power of two, so every split tiles whole rounds (see split_rounds)
LANES_ROM = GROUPS_ROM * W
# The HBM comparator's MAC array: the ROM die's lanes.  The utilisation gate
# tried the smallest array that still covers the DFlash tau-4.1 step at 8k
# (GROUPS_HBM_CANDIDATE: 6,656 groups, tiling 0.947, 100,897 effective lanes
# against a 97,471-lane need) -- it slows no 8k row, but at 2k the batch rows
# from 32 users are MAC-bound and lose 23% of their throughput, so the
# comparator keeps 131,072 lanes (qwen3_utilization.json).
GROUPS_HBM = GROUPS_ROM
LANES_HBM = GROUPS_HBM * W
GROUPS_HBM_CANDIDATE = 6656
ISA_MAX_SPLIT_AS_BUILT = 1 << ((1 << 2) - 1)    # me_split is 2 bits: S <= 8
HBM = dict(stacks=6, stack_bytes_s=1.0e12, efficiency=0.90, phy_mm2_per_stack=10.0,
           basis="HBM3E 1.0 TB/s a stack (B200: 8 TB/s over 8 stacks), 0.90 sustained "
                 "(configs/hardware/technology.json efficiencies.hbm_bandwidth); 6 stacks = the beachfront "
                 "of one reticle at 60% edge use and 12 mm a stack (H200 also carries 6)")
ROM_KV_HBM = dict(stacks=6, basis="the reticle's beachfront at 60% edge use holds 5.9 stacks of 12 mm; all 6 carry "
                                  "KV (the ROM die has no weight traffic)")
LANE_COPY_UM2 = 528.08            # routed MAC-only lane copy (ot_hdc_lane_copy, 16 lanes 8,449.24 um2, closed 1.2 GHz)
SU_SPILL_MM2 = 12.8               # the vector stream unit beyond the compute share (estimated, 25,000 um2 a lane)
DFLASH_SLOTS = 16
SPEC_SU_WIDTH = 1024              # the stream unit the spec sizes (requirements(): the one-pass softmax at 8k)


def clock_hz():
    """Slowest routed Qwen3 token-path unit (matrix engine, stream unit)."""
    return min(json.loads(p.read_text())["place_and_route"]["metrics"]["fmax_hz"] for p in (MATVEC_PHYS, STREAM_PHYS))


# -- workload -----------------------------------------------------------------------
def matrices(s=Q):
    H, NH, KV, HD, FF, V = s["H"], s["NH"], s["KV"], s["HD"], s["FF"], s["V"]
    per_layer = {"qkv": ((NH + 2 * KV) * HD, H), "o": (H, NH * HD), "gate_up": (2 * FF, H), "down": (H, FF)}
    return per_layer, {"lm_head": (V, H)}


def workload(T_ctx, s=Q, kv_bytes_per_elem=2, weight_bits=3.5):
    """Per-token work of one decode position with T_ctx positions of context."""
    L, H, NH, KV, HD, FF, V = (s[k] for k in ("L", "H", "NH", "KV", "HD", "FF", "V"))
    per_layer, head = matrices(s)
    macs = {k: L * n * k_ for k, (n, k_) in per_layer.items()}
    macs.update({k: n * k_ for k, (n, k_) in head.items()})
    macs["attn_scores"] = L * NH * HD * T_ctx
    macs["attn_pv"] = L * NH * HD * T_ctx
    weight_macs = sum(v for k, v in macs.items() if not k.startswith("attn"))
    kv_elems_read = 2 * L * KV * HD * T_ctx            # every K and V element once (GQA-shared)
    ew = {  # elementwise element-ops (one element through the stream datapath)
        "embedding_copy": H,
        "norm_scale": L * 2 * H + H,                    # input/post-attention norm + final norm
        "qk_norm": L * 2 * (NH + KV) * HD,               # sum of squares + scale
        "rope": L * (NH + KV) * HD,
        "kv_write": L * 2 * KV * HD,
        "softmax": L * 3 * NH * T_ctx,                   # max, exp(+sum), scale
        "silu_mul": L * FF,
        "residual": L * 2 * H,
        "rsqrt_recip": L * (2 + (NH + KV) + NH) + 1,
    }
    reductions = {  # (count per token, length)
        "sum_of_squares_H": (2 * L + 1, H),
        "qk_norm_HD": (L * (NH + KV), HD),
        "softmax_max_T": (L * NH, T_ctx),
        "softmax_sum_T": (L * NH, T_ctx),
        "argmax_V": (1, V),
    }
    return dict(
        context=T_ctx, macs=macs, weight_macs=weight_macs, attention_macs=macs["attn_scores"] + macs["attn_pv"],
        bytes=dict(weights_rom_format=weight_macs * weight_bits / 8, weights_bf16=2 * weight_macs,
                   weights_fp8=weight_macs, kv_read=kv_elems_read * kv_bytes_per_elem,
                   kv_write=2 * L * KV * HD * kv_bytes_per_elem,
                   kv_capacity=kv_elems_read * kv_bytes_per_elem),
        elementwise=ew, elementwise_total=sum(ew.values()), reductions=reductions)


# -- dependent-stage chain of one layer ---------------------------------------------------
# kind: 'mv' matrix-vector (a full reduction over K), 'attn' KV-sourced, 'red'
# reduction (its result needs every input), 'ew' elementwise (can chain into its
# consumer element by element), 'sfu' a few elements through a special function.
LAYER_STAGES = [
    ("attn_norm.rsqrt", "sfu", "RSQRT"), ("attn_norm.scale", "ew", "NONE"), ("qkv", "mv", None),
    ("qk_norm.sumsq", "red", "NONE"), ("qk_norm.rsqrt", "sfu", "RSQRT"), ("qk_norm.scale", "ew", "NONE"),
    ("rope", "ew", "NONE"), ("scores", "attn", None), ("softmax.max", "red", "NONE"),
    ("softmax.exp_sum", "red", "EXP"), ("softmax.recip", "sfu", "RECIP"), ("softmax.scale", "ew", "NONE"),
    ("pv", "attn", None), ("o", "mv", None), ("residual+sumsq", "red", "NONE"),
    ("ffn_norm.rsqrt", "sfu", "RSQRT"), ("ffn_norm.scale", "ew", "NONE"), ("gate_up", "mv", None),
    ("silu_mul", "ew", "SIGM"), ("down", "mv", None), ("residual+sumsq", "red", "NONE"),
]

# The spec's attention: the row max is taken on the matrix engine's result path
# as the scores emerge (a compare tree beside the argmax tree, 'mvred'), the
# stream unit makes ONE pass (exp and its sum), and the 1/Z scale moves after
# the weighted sum (32 x 128 elements instead of 32 x T; a change of the
# golden's rounding order, normalise-after-sum, as flash attention does).  The
# reciprocal then runs beside P.V, off the chain.
LAYER_STAGES_SPEC = [
    ("attn_norm.rsqrt", "sfu", "RSQRT"), ("attn_norm.scale", "ew", "NONE"), ("qkv", "mv", None),
    ("qk_norm.sumsq", "red", "NONE"), ("qk_norm.rsqrt", "sfu", "RSQRT"), ("qk_norm.scale", "ew", "NONE"),
    ("rope", "ew", "NONE"), ("scores", "attn", None), ("scores.max", "mvred", None),
    ("softmax.exp_sum", "red", "EXP"), ("pv", "attn", None), ("pv.scale", "ew", "NONE"),
    ("o", "mv", None), ("residual+sumsq", "red", "NONE"),
    ("ffn_norm.rsqrt", "sfu", "RSQRT"), ("ffn_norm.scale", "ew", "NONE"), ("gate_up", "mv", None),
    ("silu_mul", "ew", "SIGM"), ("down", "mv", None), ("residual+sumsq", "red", "NONE"),
]

AS_BUILT_LAT = dict(me_lat=T.K["me_lat"], me_tree=T.K["me_tree"], red_tail=T.K["red_tail"],
                    su={"NONE": 29, "EXP": 121, "RECIP": 75, "RSQRT": 90, "SIGM": 172}, xlane_level=6,
                    seq_gap=T.K["seq_gap"])


def split_rounds(n, k, groups, max_split=None):
    """(split, rounds, kc) of an n x k matrix under the engine's tiling rule
    (rtl/hdc/ot_hdc_matvec.sv): S = 2^split contiguous K chunks, floor(G/S)
    tiles a round, fewest cycles, the smaller split on a tie; max_split caps S
    (the ISA field)."""
    tiles = -(-n // (W * IL))
    best = None
    s = 1
    while s <= groups and (max_split is None or s <= max_split):
        if k % s == 0:
            rounds = -(-tiles // (groups // s))
            c = rounds * (k // s) * IL
            if best is None or c < best[0]:
                best = (c, s, rounds)
        s *= 2
    return best[1], best[2], k // best[1]


def mv_cycles(n, k, groups, max_split=None):
    """Engine cycles of an n x k matrix (and its split)."""
    s, rounds, kc = split_rounds(n, k, groups, max_split)
    return rounds * kc * IL, s


def tiling_eff(groups):
    """The token's weight sweep: ideal cycles over tiled cycles at this many groups."""
    per_layer, head = matrices()
    mats = [*per_layer.values()] * Q["L"] + [*head.values()]
    return sum(n * k for n, k in mats) / (W * groups) / sum(mv_cycles(n, k, groups)[0] for n, k in mats)


def attn_cycles(T_ctx, groups, s=Q, mapping="as_built"):
    """(scores, pv) engine cycles per layer.  as_built: tools/hdc_program.py's
    KV ops (scores: positions on lanes, IL heads per op, k = head_dim in order;
    P.V: head_dim on lanes, k = positions in order), each op on the groups its
    tiles cover.  ksplit: the same ops with K cut over every free group (scores
    over head_dim, P.V over positions), the chunk sums added by the split tree."""
    NH, HD = s["NH"], s["HD"]
    batches = -(-NH // IL)
    ptiles = -(-T_ctx // W)
    if mapping == "as_built":
        sc = batches * (-(-ptiles // groups)) * HD * IL
        pv = batches * (-(-(HD // W) // groups)) * T_ctx * IL
        return sc, pv
    ssc = 1
    while ssc * 2 <= HD and ptiles * ssc * 2 <= groups:
        ssc *= 2
    sc = batches * (-(-ptiles * ssc // groups)) * (HD // ssc) * IL
    spv = max(1, groups // (HD // W))
    pv = batches * (-(-T_ctx // spv)) * IL
    return sc, pv, ssc, spv


def chain(T_ctx, groups, su_width, lat, mapping, chained=True, seq_gap=None, stages=None):
    """Cycles of one layer as the sum over its dependent stages of (throughput +
    exposed latency).  An elementwise stage that chains into its consumer
    contributes only its pipeline depth; a reduction or matrix stage cannot
    produce before its last input, so its throughput and its tail are exposed.
    Returns per-stage rows and totals by component."""
    s = Q
    H, NH, KV, HD, FF = s["H"], s["NH"], s["KV"], s["HD"], s["FF"]
    per_layer, _ = matrices(s)
    lv = max(0, math.ceil(math.log2(groups)))
    me_res = lat["me_lat"] + lat["me_tree"] * lv
    xl = lat["xlane_level"] * max(0, math.ceil(math.log2(su_width))) if su_width > 1 else 0
    att = attn_cycles(T_ctx, groups, s, mapping)
    elems = {"attn_norm.scale": H, "qk_norm.sumsq": (NH + KV) * HD, "qk_norm.scale": (NH + KV) * HD,
             "rope": (NH + KV) * HD, "softmax.max": NH * T_ctx, "softmax.exp_sum": NH * T_ctx,
             "softmax.scale": NH * T_ctx, "residual+sumsq": H, "ffn_norm.scale": H, "silu_mul": FF,
             "attn_norm.rsqrt": 1, "qk_norm.rsqrt": NH + KV, "softmax.recip": NH, "ffn_norm.rsqrt": 1,
             "pv.scale": NH * HD}
    rows = []
    tot = dict(weights=0, attention=0, elementwise=0, latency=0, control=0)
    for name, kind, cls in (stages or LAYER_STAGES):
        if kind == "mvred":             # a compare tree over the result lanes: 2 cycles a level
            thr, ex, comp = 0, 2 * max(1, math.ceil(math.log2(groups * W))), "elementwise"
        elif kind == "mv":
            thr, _ = mv_cycles(*per_layer[name], groups)
            ex = me_res
            comp = "weights"
        elif kind == "attn":
            thr = att[0] if name == "scores" else att[1]
            ex = me_res
            comp = "attention"
        else:
            n = elems[name]
            thr = -(-n // su_width)
            ex = lat["su"][cls] + (lat["red_tail"] + xl if kind == "red" else 0)
            comp = "elementwise"
            if kind == "ew" and chained:
                thr = 0                # hidden under the consumer's loop
        g = lat["seq_gap"] if seq_gap is None else seq_gap
        rows.append(dict(stage=name, kind=kind, throughput=thr, exposed_latency=ex))
        tot[comp] += thr
        tot["latency"] += ex
        tot["control"] += g
    return rows, tot


def roofline_rom(wl, clock, groups=GROUPS_ROM, su_width=SPEC_SU_WIDTH, kv_fmt=KV_FMT_SPEC):
    lanes = groups * W
    bw = rom_kv_bw()
    r = {"weights_mac": wl["weight_macs"] / lanes, "attention_mac": wl["attention_macs"] / lanes,
         "kv_hbm_read": kv_bytes(wl, kv_fmt) / bw * clock, "elementwise": wl["elementwise_total"] / su_width}
    return {k: dict(cycles=round(v), us=round(v / clock * 1e6, 3)) for k, v in r.items()}


def hbm_design(wl, clock, fmt, kv_fmt=KV_FMT_SPEC):
    """The iso-area HBM comparator: weights (fmt) and KV (kv_fmt) streamed."""
    bw = HBM["stacks"] * HBM["stack_bytes_s"] * HBM["efficiency"]
    wbytes = {"bf16": wl["bytes"]["weights_bf16"], "fp8": wl["bytes"]["weights_fp8"],
              "rom_format_3.5b": wl["bytes"]["weights_rom_format"]}[fmt]
    kvb = kv_bytes(wl, kv_fmt)
    t = (wbytes + kvb) / bw
    mac_rate = wl["weight_macs"] / t
    return dict(weight_format=fmt, kv_format=kv_fmt, bytes_per_token=wbytes + kvb, sustained_bytes_s=bw,
                token_s=t, tokens_s=round(1 / t, 1), mac_rate_needed=mac_rate,
                lanes_needed_at_clock=math.ceil(mac_rate / clock), hbm_bytes_per_cycle=round(bw / clock))


# -- the ROM reticle with its KV in HBM --------------------------------------------------
def rom_kv_bw():
    return ROM_KV_HBM["stacks"] * HBM["stack_bytes_s"] * HBM["efficiency"]


def kv_bytes(wl, fmt):
    return wl["bytes"]["kv_read"] * KV_FORMATS[fmt] / 2


def area_ledger():
    """The reticle once the KV SRAM is freed (user decision: users' KV lives in
    HBM): the 259.6 mm2 of SRAM goes to the KV stacks' PHYs, the KV prefetch
    buffer, the DFlash drafter's ROM, the stream unit's spill beyond the
    compute share, and MAC lane copies (the lane multiplier m) at the measured
    MAC-only copy area."""
    freed = RETICLE["sram_mm2"]
    phy = ROM_KV_HBM["stacks"] * HBM["phy_mm2_per_stack"]
    buf_bytes = kv_prefetch_buffer_bytes()
    buf = buf_bytes * 8 / SRAM_BITS_PER_MM2
    drafter = DRAFTER_PARAMS / 8.190735e9 * RETICLE["rom_mm2"]
    su_spill = SU_SPILL_MM2
    rest = freed - phy - buf - drafter - su_spill
    copy_mm2 = LANES_ROM * LANE_COPY_UM2 * 1e-6
    copies = max(0, int(rest // copy_mm2))
    return dict(freed_sram_mm2=freed, hbm_phy_mm2=phy, kv_prefetch_buffer_mm2=round(buf, 1),
                kv_prefetch_buffer_bytes=buf_bytes, drafter_rom_mm2=round(drafter, 1),
                stream_unit_spill_mm2=su_spill, lane_copy_mm2=round(copy_mm2, 1), lane_copies_added=copies,
                lane_multiplier_m=1 + copies, slack_mm2=round(rest - copies * copy_mm2, 1),
                beachfront_mm=2 * (26 + 33) * 0.6, stacks_max_by_beachfront=round(2 * (26 + 33) * 0.6 / 12), stacks_note="5.9 by the 60%-edge rule; 6 as on the 814 mm2 GH100 die (H100/H200)",
                lane_copy_basis="routed ot_hdc_lane_copy (16 lanes: the exact BF16 multiplier, the circulating "
                                "FP32 adder and its interleave registers, sharing the group's weight word; the "
                                "split tree, result port and argmax shared): 8,449 um2, closed at 1.2 GHz "
                                "(results/physical_abi3/asap7/hdc/ot_hdc_lane_copy/physical.json)")


T_RFC_S = 350e-9                  # HBM3E all-bank refresh (the controller rules, section 12)


def kv_prefetch_buffer_bytes(ctx=CTX_HEAD, fmt=KV_FMT_SPEC):
    """A RING of one layer of KV at the head context plus the stream's
    refresh cover (bandwidth x tRFC).  The stream runs continuously (it binds
    the token) and the engine drains a layer's KV in its attention burst, so
    the peak occupancy is the layer being consumed plus what lands while a
    channel refreshes.  (Two layers, double-buffered, was the first sizing:
    the utilisation gate found it half used -- qwen3_utilization.json.)"""
    return kv_bytes(workload(ctx), fmt) / Q["L"] + rom_kv_bw() * T_RFC_S


def rom_token(out, ctx, fmt, slots=1, users=1, m=1, drafter=False):
    """Cycles of one step on the ROM reticle: the dependency chain's latency
    (shared by every slot and user) plus unit work, against the KV stream.
    Slots (speculative positions of ONE user) share the KV reads and the
    weight words; users share weight words only.  Lane copies m divide the
    weight and attention MAC work of positions that share their operand word
    (slots: weights and KV; users: weights)."""
    comp = out["dependency_chain"][f"{ctx}/spec"]["components"]
    lat = comp["latency"] + comp["control"]
    Wc, A, E = comp["weights"], comp["attention"], comp["elementwise"]
    n = slots * users
    compute = lat + math.ceil(n / m) * Wc + (math.ceil(slots / m) * users) * A + n * E
    kvb = users * kv_bytes(out["workload"][str(ctx)], fmt) * ((1 + DRAFTER_LAYERS / Q["L"]) if drafter else 1)
    kv = kvb / rom_kv_bw() * CLOCK[0]
    return max(compute, kv), compute, kv


BUDGET_SHARES = dict(attention=0.15, elementwise=0.10, latency=0.30, control=0.03)


def budget(out, clock):
    """Target per context and KV format = max(the weight sweep over 55% of the
    token, the KV stream over 95% of it); the non-weight shares of that target
    are the blocks' budgets.  The spec's design point: 8k, FP8 KV."""
    per_layer, head = matrices()
    wl = out["workload"][str(CTX_HEAD)]
    w_cyc = Q["L"] * sum(mv_cycles(n, k, GROUPS_ROM)[0] for n, k in per_layer.values()) + \
        sum(mv_cycles(n, k, GROUPS_ROM)[0] for n, k in head.values())
    ideal = wl["weight_macs"] / LANES_ROM
    targets = {}
    for ctx in CONTEXTS:
        for fmt in KV_FORMATS:
            kvc = kv_bytes(out["workload"][str(ctx)], fmt) / rom_kv_bw() * clock
            tgt = max(ideal / 0.55, kvc / 0.95)
            targets[f"{ctx}/{fmt}"] = dict(context=ctx, kv_format=fmt, kv_stream_cycles=round(kvc),
                                           target_cycles=round(tgt), target_tokens_s=round(clock / tgt, 1),
                                           binding="kv_stream" if kvc / 0.95 > ideal / 0.55 else "weights")
    head_t = targets[f"{CTX_HEAD}/{KV_FMT_SPEC}"]
    target = head_t["target_cycles"]
    alloc = {k: round(v * target) for k, v in BUDGET_SHARES.items()}
    alloc["weights"] = round(ideal)
    return dict(context=CTX_HEAD, kv_format=KV_FMT_SPEC, weight_sweep_ideal_cycles=round(ideal),
                weight_sweep_tiled_cycles=w_cyc, weight_tiling_efficiency=round(ideal / w_cyc, 4),
                target_cycles=target, target_tokens_s=head_t["target_tokens_s"],
                ceiling_tokens_s=round(clock / ideal, 1), binding=head_t["binding"],
                shares=dict(BUDGET_SHARES, weights=round(ideal / target, 4)), cycles=alloc, targets=targets)


def requirements(out, clock):
    """Per-block requirements at the design point (8k, FP8 KV, batch 1)."""
    bud = out["budget"]
    L, NH, HD, KV = Q["L"], Q["NH"], Q["HD"], Q["KV"]
    cyc = bud["cycles"]
    ctx = CTX_HEAD
    wl = out["workload"][str(ctx)]
    stages = len(LAYER_STAGES_SPEC)
    attn_lanes = wl["attention_macs"] / cyc["attention"]
    su_w = 1
    while su_w < 1 << 14 and L * chain(ctx, GROUPS_ROM, su_w, dict(AS_BUILT_LAT, seq_gap=1), "ksplit", True,
                                        stages=LAYER_STAGES_SPEC)[1]["elementwise"] > cyc["elementwise"]:
        su_w *= 2
    lat_stage = cyc["latency"] / (L * stages)
    kvb = kv_bytes(wl, KV_FMT_SPEC)
    ledger = out["area"]
    return dict(
        mac_lanes=dict(requirement=LANES_ROM, basis="8,192 groups of 16: the weight sweep binds the compute share"),
        lane_multiplier=dict(requirement=ledger["lane_multiplier_m"],
                             basis="MAC-only lane copies in the freed SRAM (area ledger); they serve speculative "
                                   "slots and batched users"),
        weight_tiling_efficiency=dict(requirement=">= 0.90 of the ideal sweep (split/tile quantisation)"),
        rom_read_bytes_per_cycle=dict(requirement=round(LANES_ROM * RETICLE["weight_bits"] / 8),
                                      basis="one weight per lane per cycle at the ROM format"),
        attention_lanes_min=dict(requirement=math.ceil(attn_lanes),
                                 basis=f"{wl['attention_macs']:.3e} MACs in {cyc['attention']} cycles"),
        kv_hbm=dict(stacks=ROM_KV_HBM["stacks"], format=KV_FMT_SPEC, bytes_per_token=kvb,
                    sustained_bytes_s=rom_kv_bw(), stream_cycles=round(kvb / rom_kv_bw() * clock),
                    efficiency_min="0.90 of raw peak with refresh on (REFab measured 0.904 / 0.910)",
                    controller_queue_beats_per_pseudo_channel_min=512,
                    prefetch="layer l+1's KV (positions < t) streams while layer l computes; the token's own K/V "
                             "row is kept on die (tail buffer) and written back behind the stream",
                    prefetch_buffer_bytes=ledger["kv_prefetch_buffer_bytes"],
                    streamer="rtl/hdc/kv/ot_hdc_kv_stream.sv extended to the K-split attention word order"),
        stream_unit_elements_per_cycle=dict(requirement=su_w,
                                            basis=f"the spec chain's exposed elementwise cycles at 8k within "
                                                  f"{cyc['elementwise']}"),
        reduction_tree=dict(requirement=f"lane partials + a {int(math.log2(su_w))}-level cross-lane pairwise tree"),
        exposed_latency_per_dependent_stage_max=dict(
            requirement=round(lat_stage), stages_per_layer=stages,
            basis=f"{cyc['latency']} cycles over {L} layers x {stages} dependent stages"),
        instruction_issue=dict(requirement=f"<= {cyc['control']} control cycles a token exposed",
                               per_instruction_max=round(cyc["control"] / 4540, 2)),
        argmax=dict(requirement="streaming compare tree over each result word (as built)"),
        vector_buffer=dict(requirement_elements=max(2 * Q["FF"], NH * ctx),
                           basis="score/probability rows (NH x T at 8k) and gate/up outputs"))


def capped_layout(groups, max_split):
    """tools/hdc_timing.ShapeLayout with every matrix's split capped (the ISA's
    me_split field) and tiled by the RTL's floor(G/S) rule."""
    lay = T.ShapeLayout(Q, groups)
    for key, m in lay.mat.items():
        s, rounds, kc = split_rounds(m["n"], m["k"] * m["split"], groups, max_split)
        m.update(k=kc, tiles=rounds, split=s)
    return lay


def layer_chain(prog, iss, d, T_ctx, groups, layer=None):
    """One decoder layer of the replayed program (the middle one), cut at the
    matrix engine's weight-op issues: each stage's span in cycles, the engine's
    busy cycles in it (the weight sweep, or the attention passes), and the rest,
    the exposed chain (stream-unit work and latency not hidden under the engine)."""
    me = [i for i, f in enumerate(prog) if f.get("unit") == I.UNIT_ME]
    wt = [i for i in me if not prog[i].get("me_wsrc") and not prog[i].get("me_amax")]
    layer = Q["L"] // 2 if layer is None else layer
    q0, o, gu, dn, q1 = (wt[4 * layer + j] for j in range(5))

    def busy(lo, hi):
        tot = 0
        for i in me:
            if lo <= i < hi:
                f = {n: prog[i].get(n, 0) for n, _ in I.FIELDS}
                rr, kk = T.me_loop(f, d, T_ctx - 1, groups)
                tot += rr * kk * IL
        return tot
    att0 = next(i for i in me if q0 < i and prog[i].get("me_wsrc"))
    cuts = (("QKV projection, then q/k norm, RoPE", q0, att0),
            ("attention: scores, softmax, P·V, 1/Z", att0, o),
            ("O projection, residual, FFN norm", o, gu),
            ("gate/up projection, fused SiLU·up", gu, dn),
            ("down projection, residual, next norm", dn, q1))
    rows = []
    for name, lo, hi in cuts:
        span = iss[hi] - iss[lo]
        b = busy(lo, hi)
        rows.append(dict(stage=name, cycles=span, engine_busy=b, exposed=span - b))
    return dict(layer=layer, cycles=iss[q1] - iss[q0], stages=rows)


def as_built(T_ctx, groups=GROUPS_ROM, su_width=SPEC_SU_WIDTH, max_split=None, lv=None):
    """The calibrated sequencer model replaying the decode program the core runs
    AT THIS COMMIT (tools/hdc_program.build_program) at the shipped shapes,
    with the RTL's parameters set to the spec's (8,192 groups, a stream unit of
    SPEC_SU_WIDTH lanes whose reducer has LV = log2(max segment vectors) time
    levels), KV on core (the KV stream is priced separately): cycles and their
    attribution (unit busy by class, sequencer stalls).  The pre-work figures
    (7,680 groups, split <= 8, a 1-wide stream unit) are frozen in BASELINE."""
    import collections
    import hdc_program as P
    if lv is None:
        lv = max(1, math.ceil(math.log2(max(T_ctx, Q["H"]) / su_width))) if su_width > 1 else 0
    sw0 = I.SU_WIDTH
    I.SU_WIDTH = su_width            # the program's chase thresholds count vectors of this width
    try:
        lay = capped_layout(groups, max_split)
        prog = P.build_program(lay)
    finally:
        I.SU_WIDTH = sw0
    dyn = dict(H=Q["H"], half=Q["HD"] // 2, HD=Q["HD"])
    tr = []
    k = dict(T.K, red_lv=lv)
    iss, cyc = T.simulate(prog, T_ctx - 1, groups=groups, dyn_shape=dyn, su_width=su_width, trace=tr, k=k)
    d = T.dyn_values(T_ctx - 1, groups=groups, **dyn)
    busy = collections.Counter()
    stall = collections.Counter()
    for f, (why, g) in zip(prog, tr):
        f = {n: f.get(n, 0) for n, _ in I.FIELDS}
        if f["unit"] == I.UNIT_ME:
            c = "attn_scores" if f["me_wsrc"] and f["me_d_tiles"] else "attn_pv" if f["me_wsrc"] else \
                "lm_head" if f["me_amax"] else "weights"
            rr, kk = T.me_loop(f, d, T_ctx - 1, groups)
            busy[c] += rr * kk * IL
        elif f["unit"] == I.UNIT_SU:
            busy["stream"] += T.su_vectors(f, d, su_width)
        stall[why] += g
    n = sum(1 for f in prog if f.get("unit") != I.UNIT_END)
    return dict(context=T_ctx, groups=groups, su_width=su_width, reducer_time_levels=lv, max_split=max_split,
                instructions=n, cycles=cyc, layer_chain=layer_chain(prog, iss, d, T_ctx, groups),
                unit_busy=dict(busy), sequencer_stalls={k: v for k, v in stall.items() if k != "issue"},
                seq_gap_total=n * T.K["seq_gap"])


def evaluate():
    clock = clock_hz()
    CLOCK[0] = clock
    out = dict(schema=SCHEMA, tool="tools/arch_budget_qwen3.py", model="Qwen3-8B", shape=Q, clock_hz=clock,
               clock_basis="slowest routed Qwen3 token-path unit (ot_hdc_matvec, ot_hdc_stream; ASAP7 TT)",
               design_point=dict(context=CTX_HEAD, kv_format=KV_FMT_SPEC, batch=1,
                                 decision="user: 8k is the target context; users' KV lives in HBM on the ROM die"),
               reticle=RETICLE, rom_design=dict(groups=GROUPS_ROM, lanes=LANES_ROM, mac_um2_asap7=MAC_UM2,
                                                kv_hbm=ROM_KV_HBM),
               hbm_design=HBM)
    out["workload"] = {str(t): workload(t) for t in CONTEXTS}
    out["area"] = area_ledger()
    out["roofline_rom"] = {str(t): roofline_rom(out["workload"][str(t)], clock) for t in CONTEXTS}
    out["hbm_comparator"] = {str(t): {f: hbm_design(out["workload"][str(t)], clock, f)
                                      for f in ("bf16", "fp8", "rom_format_3.5b")} for t in CONTEXTS}
    spec_lat = dict(AS_BUILT_LAT, seq_gap=1)
    chains = {}
    for t in CONTEXTS:
        for label, sw, lat, mp, ch, st in (
                ("as_built_units", 1, AS_BUILT_LAT, "as_built", False, LAYER_STAGES),
                ("spec_widths_reference_graph", SPEC_SU_WIDTH, AS_BUILT_LAT, "ksplit", True, LAYER_STAGES),
                ("spec", SPEC_SU_WIDTH, spec_lat, "ksplit", True, LAYER_STAGES_SPEC)):
            rows, tot = chain(t, GROUPS_ROM, sw, lat, mp, ch, stages=st)
            layer = sum(tot.values())
            per_tok = {k: v * Q["L"] for k, v in tot.items()}
            per_tok["weights"] += mv_cycles(Q["V"], Q["H"], GROUPS_ROM)[0]
            total = sum(per_tok.values())
            chains[f"{t}/{label}"] = dict(context=t, su_width=sw, attention_mapping=mp, chained_elementwise=ch,
                                          layer_cycles=layer, token_cycles=total, components=per_tok,
                                          tokens_s=round(clock / total, 1), stages=rows)
    out["dependency_chain"] = chains
    out["budget"] = budget(out, clock)
    out["requirements"] = requirements(out, clock)
    # the spec machine's token: its chain against the KV stream, per context and format
    out["rom_token"] = {}
    for t in CONTEXTS:
        for fmt in KV_FORMATS:
            step, comp, kv = rom_token(out, t, fmt)
            out["rom_token"][f"{t}/{fmt}"] = dict(cycles=round(step), compute_cycles=round(comp),
                                                 kv_stream_cycles=round(kv), tokens_s=round(clock / step, 1),
                                                 binding="kv_stream" if kv > comp else "compute")
    out["baseline_as_built"] = json.loads(BASELINE.read_text())
    out["as_built_calibrated"] = {str(t): as_built(t) for t in CONTEXTS}
    out["gap"] = gap_table(out)
    out["hbm_requirements"] = hbm_requirements(out, clock)
    out["dflash"] = dflash_budget(out, clock)
    out["batch"] = batch_model(out, clock)
    out["power"] = power_budget(out, clock)
    return out


UTIL_OUT = ROOT / "results/arch/qwen3_utilization.json"
SRAM_READ_B_PER_CYCLE = GROUPS_ROM * W   # the engine's KV port: one FP8 word of W elements a group a cycle


def _blk(name, peak, unit, demand, step, *, busy=None, area_mm2=None, kind="compute", **kw):
    u = demand / (peak * step) if peak else 0.0
    r = dict(block=name, kind=kind, peak_per_cycle=peak, unit=unit, demand_per_step=demand,
             utilization=round(u, 4))
    if busy is not None:
        r["busy_cycles"] = round(busy)
        r["busy_fraction"] = round(busy / step, 4)
    if area_mm2 is not None:
        r["area_mm2"] = area_mm2
    r.update(kw)
    return r


def utilization(out, clock):
    """The utilisation gate (user, binding before the core P&R): for every block
    of the ROM reticle and of the HBM comparator, its peak, its demand at batch
    1 (autoregressive and DFlash tau 4.1), at the KV-bound batch and at the
    largest batch; utilisation (MFU for compute, MBU for memory and bandwidth)
    and busy fraction over the step; area and energy share; and a verdict:
    RIGHT-SIZED (binding, or smaller would slow the single user -- measured by
    the calibrated model where it can be), JUSTIFIED (idle capacity that buys
    batch-1 latency), or OVER-PROVISIONED with the right-sizing applied."""
    wl = out["workload"][str(CTX_HEAD)]
    m = out["area"]["lane_multiplier_m"]
    ar = out["as_built_calibrated"][str(CTX_HEAD)]
    kvb1 = kv_bytes(wl, KV_FMT_SPEC)
    kv_cyc = kvb1 / rom_kv_bw() * clock
    macs_tok = wl["weight_macs"] + wl["attention_macs"]
    per_layer, _ = matrices()
    layer_macs = sum(a * b for a, b in per_layer.values())
    wbytes = wl["bytes"]["weights_rom_format"]
    drafter_bytes = DRAFTER_PARAMS * RETICLE["weight_bits"] / 8
    rom_peak_b = LANES_ROM * RETICLE["weight_bits"] / 8
    raw_hbm_b = ROM_KV_HBM["stacks"] * HBM["stack_bytes_s"] / clock
    trans = Q["NH"] * CTX_HEAD * Q["L"] + Q["FF"] * Q["L"] + wl["elementwise"]["rsqrt_recip"]
    red = sum(n * k for n, k in wl["reductions"].values())
    layer_kv = kvb1 / Q["L"]
    ring_need = layer_kv + rom_kv_bw() * T_RFC_S
    buf = out["area"]["kv_prefetch_buffer_bytes"]
    buf_first = 2 * layer_kv
    batch = {r["batch"]: r for r in out["batch"]["per_context"][str(CTX_HEAD)]["rom"] if r["lane_multiplier"] == m}
    b_kv = min(b for b, r in batch.items() if r["binding"] == "kv_stream")
    b_max = max(batch)
    best = out["dflash"]["rom"][f"{CTX_HEAD}/{KV_FMT_SPEC}/m{m}"]["best"]
    Bd = best["block"]
    draft_macs = Bd * DRAFTER_LAYERS * layer_macs + (Bd - 1) * Q["V"] * Q["H"] + Bd * DFLASH_FC[0] * DFLASH_FC[1]
    area = out["area"]
    ub = ar["unit_busy"]
    attn_busy = ub["attn_scores"] + ub["attn_pv"]
    # scenarios: (label, step cycles, positions sharing a weight word, users, slots, drafter, basis)
    scen = [("ar_batch1", max(ar["cycles"], kv_cyc), 1, 1, 1, False,
             "calibrated sequencer model at HEAD (unit busy measured on the replayed program)"),
            (f"dflash_tau{TAU_CENTRAL}_block{Bd}", best["step_cycles"], min(m, Bd), 1, Bd, True,
             f"budget model, best ROM block at m = {m} ({best['tokens_per_step']} tokens a step)"),
            (f"kv_bound_batch{b_kv}", batch[b_kv]["step_cycles"], min(m, b_kv), b_kv, 1, False,
             "budget model, smallest KV-bound batch"),
            (f"max_batch{b_max}", batch[b_max]["step_cycles"], m, b_max, 1, False, "budget model")]
    rom = {}
    for label, step, share, users, slots, drafter, basis in scen:
        n = users * slots
        macs = n * macs_tok + (draft_macs if drafter else 0)
        k = max(1, min(m, share))
        sweeps = 1 if drafter else math.ceil(n / m)
        rbytes = sweeps * wbytes + (drafter_bytes if drafter else 0)
        kvb = users * kvb1 * ((1 + DRAFTER_LAYERS / Q["L"]) if drafter else 1)
        su_el = n * wl["elementwise_total"]
        su_busy = ub["stream"] * n
        a_busy = attn_busy * users * math.ceil(slots / k)
        me_busy = (ub["weights"] + ub["lm_head"]) * math.ceil(n / k) + a_busy
        if drafter:
            me_busy += draft_macs / (LANES_ROM * k)
        instr = ar["instructions"] * users * (1 + (DRAFTER_LAYERS / Q["L"] if drafter else 0))
        t = step / clock
        e = dict(matrix_engine=macs * E_ME_PER_MAC, other_logic_upper=macs * (E_LOGIC_PER_MAC - E_ME_PER_MAC),
                 rom_read=rbytes * E_ROM_PER_BYTE, rom_leakage=LEAK_W_ROM * t,
                 kv_hbm_stacks=kvb * E_HBM_PER_BYTE)
        et = sum(e.values())
        blocks = [
            _blk("matrix engine, base lanes", LANES_ROM, "MAC", macs / k, step, busy=min(me_busy, step),
                 area_mm2=RETICLE["compute_mm2"], kind="compute (MFU)"),
            _blk(f"matrix engine, {m - 1} lane copies", LANES_ROM * (m - 1), "MAC", macs * (k - 1) / k, step,
                 busy=min(me_busy, step) if k > 1 else 0, area_mm2=round(area["lane_copy_mm2"] * (m - 1), 1),
                 kind="compute (MFU)", copies_in_use=k - 1),
            _blk("weight ROM macros and read path", rom_peak_b, "byte", rbytes, step,
                 busy=rbytes / rom_peak_b, area_mm2=RETICLE["rom_mm2"], kind="memory (MBU)", weight_sweeps=sweeps),
            _blk("drafter ROM", rom_peak_b, "byte", drafter_bytes if drafter else 0, step,
                 area_mm2=area["drafter_rom_mm2"], kind="memory (MBU)"),
            _blk("attention path (engine share: scores, P.V)", LANES_ROM * k, "MAC",
                 n * wl["attention_macs"], step, busy=a_busy, kind="compute (MFU)"),
            _blk(f"vector stream unit ({SPEC_SU_WIDTH} lanes)", SPEC_SU_WIDTH, "element", su_el, step,
                 busy=min(su_busy, step), area_mm2=SU_SPILL_MM2, kind="compute (MFU)"),
            _blk("SFUs (exp, SiLU, rsqrt/recip: one a stream lane)", SPEC_SU_WIDTH, "transcendental", n * trans,
                 step, kind="compute (MFU)"),
            _blk("reducers (R-ARITH segments, split tree)", SPEC_SU_WIDTH, "element", n * red, step,
                 kind="compute (MFU)"),
            _blk("KV streamer, HBM controllers and PHYs (6 stacks, raw peak)", raw_hbm_b, "byte", kvb, step,
                 busy=min(kvb / (raw_hbm_b * HBM["efficiency"]), step), area_mm2=area["hbm_phy_mm2"],
                 kind="bandwidth (MBU)",
                 mbu_of_sustained=round(kvb / (raw_hbm_b * HBM["efficiency"] * step), 4)),
            _blk("KV ring buffer (SRAM): capacity", buf, "byte", ring_need, 1,
                 area_mm2=area["kv_prefetch_buffer_mm2"], kind="capacity",
                 first_sizing_bytes=buf_first, first_sizing_utilization=round(ring_need / buf_first, 4)),
            _blk("KV ring buffer (SRAM): engine read port", SRAM_READ_B_PER_CYCLE, "byte", kvb, step,
                 busy=kvb / SRAM_READ_B_PER_CYCLE, kind="bandwidth (MBU)"),
            _blk("sequencer / issue", 1, "instruction", instr, step, busy=instr, kind="control"),
            _blk("argmax (streaming compare tree on the LM head's results)", LANES_ROM, "compare",
                 Q["V"] * (n + (Bd - 1 if drafter else 0)), step,
                 busy=ub["lm_head"] * math.ceil(n / k), kind="compute"),
        ]
        rom[label] = dict(step_cycles=round(step), basis=basis, users=users, slots=slots,
                          tokens_s_total=round(users * (best["tokens_per_step"] if drafter else 1) * clock / step, 1),
                          energy_per_step_mj={k2: round(v * 1e3, 3) for k2, v in e.items()},
                          energy_share={k2: round(v / et, 4) for k2, v in e.items()}, blocks=blocks)
    # ---- the HBM comparator (FP8 weights and KV, the same 6 stacks) -------------------------------
    bw = HBM["stacks"] * HBM["stack_bytes_s"] * HBM["efficiency"]
    raw = HBM["stacks"] * HBM["stack_bytes_s"] / clock
    comp = out["dependency_chain"][f"{CTX_HEAD}/spec"]["components"]
    lat = (comp["latency"] + comp["control"]) / clock
    dh = out["dflash"]["hbm"]["fp8"]
    n16 = DFLASH_SLOTS
    step_macs16 = n16 * DRAFTER_LAYERS * layer_macs + (n16 - 1) * Q["V"] * Q["H"] + \
        n16 * (Q["L"] * layer_macs + Q["V"] * Q["H"]) + n16 * wl["attention_macs"]
    hbatch = [r["batch"] for r in out["batch"]["per_context"][str(CTX_HEAD)]["hbm"]["fp8"]]
    hb_kv = min(b for b in hbatch if b * kvb1 >= wl["weight_macs"])
    wl2 = out["workload"]["2048"]
    kvb2 = kv_bytes(wl2, KV_FMT_SPEC)
    hscen = [("ar_batch1", 1, None, wl, kvb1), (f"dflash_tau{TAU_CENTRAL}_block{n16}", None, dh["step_s"], wl, kvb1),
             (f"kv_bound_batch{hb_kv}", hb_kv, None, wl, kvb1), (f"max_batch{b_max}", b_max, None, wl, kvb1),
             (f"ctx2048_max_batch{b_max}", b_max, None, wl2, kvb2)]
    hbm = {}
    for lanes, groups, role in ((LANES_HBM, GROUPS_HBM, "the comparator as specified"),
                                (GROUPS_HBM_CANDIDATE * W, GROUPS_HBM_CANDIDATE, "right-sizing candidate, rejected")):
        eff = tiling_eff(groups)
        rows = {}
        for label, B, fixed, w_, kvb_ in hscen:
            if fixed:
                macs = step_macs16
                byt = (w_["weight_macs"] + DRAFTER_PARAMS) + kvb_ * (1 + DRAFTER_LAYERS / Q["L"])
                bound_t = fixed
                t = max(fixed, macs / (lanes * eff * clock))
            else:
                byt = w_["weight_macs"] + B * kvb_
                macs = B * (w_["weight_macs"] + w_["attention_macs"])
                bound_t = max(byt / bw, lat)
                t = max(bound_t, macs / (lanes * eff * clock))
            step = t * clock
            rows[label] = dict(step_cycles=round(step), slowed_by_lanes=round(t / bound_t - 1, 4), blocks=[
                _blk("matrix engine", lanes, "MAC", macs, step, busy=macs / (lanes * eff), kind="compute (MFU)"),
                _blk("HBM (6 stacks, raw peak): weights + KV", raw, "byte", byt, step,
                     busy=min(byt / (raw * HBM["efficiency"]), step), kind="bandwidth (MBU)",
                     mbu_of_sustained=round(byt / (bw / clock * step), 4)),
                _blk(f"vector stream unit ({SPEC_SU_WIDTH} lanes)", SPEC_SU_WIDTH, "element",
                     (B or n16) * w_["elementwise_total"], step, kind="compute (MFU)"),
                _blk("sequencer / issue", 1, "instruction", ar["instructions"] * (B or 1), step, kind="control"),
            ])
        hbm[f"{lanes}_lanes"] = dict(role=role, groups=groups, lanes=lanes, tiling_efficiency=round(eff, 4),
                                     scenarios=rows)
    su_sweep = {sw: as_built(CTX_HEAD, su_width=sw)["cycles"] for sw in (512, 1024, 2048)}
    g_half = as_built(CTX_HEAD, groups=GROUPS_ROM // 2)["cycles"]
    ar_step = max(ar["cycles"], kv_cyc)
    verdicts = [
        dict(block="ROM: matrix engine base lanes (131,072)", verdict="RIGHT-SIZED",
             why=f"compute sits at the KV floor ({ar['cycles']:,} vs {round(kv_cyc):,} cycles); half the groups "
                 f"is {g_half:,} cycles (+{g_half / ar_step - 1:.0%} a token) in the calibrated model"),
        dict(block=f"ROM: {m - 1} lane copies", verdict="JUSTIFIED (DFlash only), conditional on power",
             why=f"idle in autoregressive decode and in KV-bound batches (each user's KV is its own); they carry "
                 f"the DFlash block-{Bd} verify ({best['speedup']}x single-user tokens/s). Under the cooling limit "
                 f"that gain needs <= {out['power']['pj_per_mac_required_dflash']} pJ/MAC; at the measured 3.97 "
                 f"the capped DFlash rate is below autoregressive and the copies would not pay"),
        dict(block="ROM: weight ROM read path", verdict="RIGHT-SIZED",
             why="one weight a lane a cycle; the sweep is on the single user's chain (57,740 cycles)"),
        dict(block="ROM: vector stream unit (1,024 lanes; SFUs and reducers on its lanes)", verdict="RIGHT-SIZED",
             why=f"calibrated: 512 lanes is {su_sweep[512]:,} cycles, above the KV floor "
                 f"(+{su_sweep[512] / ar_step - 1:.1%} a token); 2,048 is {su_sweep[2048]:,}, under the floor, "
                 f"so it buys nothing"),
        dict(block="ROM: KV streamer, controllers, 6 PHYs", verdict="RIGHT-SIZED (binding)",
             why="the KV stream binds the token from batch 1 (0.3% below compute) and at every batch"),
        dict(block="ROM: KV ring buffer", verdict="OVER-PROVISIONED -> RIGHT-SIZED (applied)",
             why=f"two layers ({buf_first / 1e6:.1f} MB) were {ring_need / buf_first:.0%} used: the stream is "
                 f"continuous and the engine drains a layer in its attention burst, so the peak is one layer plus "
                 f"the refresh cover ({buf / 1e6:.1f} MB); area_ledger now sizes the ring"),
        dict(block="ROM: KV ring buffer's engine read port", verdict="JUSTIFIED (latency)",
             why="one FP8 word a group a cycle is the engine's attention operand rate: the scores and P.V passes "
                 f"read a layer's KV in {attn_busy // Q['L']} cycles on the chain; a narrower port lengthens "
                 "every layer's attention stage"),
        dict(block="ROM: drafter ROM", verdict="JUSTIFIED (DFlash only)", why="read once a DFlash step; idle otherwise"),
        dict(block="ROM: sequencer, argmax", verdict="JUSTIFIED (latency)",
             why="small; both sit on the token's chain (the issue gap, the LM head's tail)"),
        dict(block="HBM: matrix engine", verdict="JUSTIFIED (batch throughput), right-sizing rejected",
             why=f"{LANES_HBM:,} lanes are 4.6% used at batch 1 and bytes bind every 8k row, but at 2k the rows "
                 f"from 32 users are MAC-bound (utilisation ~1). The smallest array that keeps the DFlash step "
                 f"({GROUPS_HBM_CANDIDATE * W:,} lanes, tiling {tiling_eff(GROUPS_HBM_CANDIDATE):.3f}, against a "
                 f"{dh['mac_lanes_min']:,}-lane need) slows no single user and no 8k row, but costs the 2k batch "
                 f"rows 23% of their throughput; the comparator keeps its lanes rather than be handicapped"),
        dict(block="HBM: stacks and controllers", verdict="RIGHT-SIZED (binding)",
             why="bytes bind every 8k row and the 2k rows below 32 users"),
    ]
    return dict(schema="opentallas.arch-utilization-qwen3.v1", tool="tools/arch_budget_qwen3.py",
                context=CTX_HEAD, kv_format=KV_FMT_SPEC, clock_hz=clock, lane_multiplier=m,
                rule="improve utilisation without slowing the single user",
                rom=rom, hbm=hbm, su_width_sweep_cycles=su_sweep, half_groups_cycles=g_half,
                verdicts=verdicts, energy_basis=out["batch"]["energy_basis"],
                notes=["busy fractions of the autoregressive row are the calibrated model's; the other rows "
                       "scale the per-position busy by positions over copies in use",
                       "SFU and reducer demand counts operations whose peak is the stream unit's lanes; their "
                       "busy time is inside the stream unit's",
                       "the other rows' steps are the budget model's (analytical chain, conservative against the "
                       "calibrated 123,301); KV-bound rows are exact either way"])



def hbm_requirements(out, clock):
    """The iso-area HBM comparator: the weight stream binds, so the design goal
    is a stream that never stalls.  Weights are data-independent, so the
    stream runs ahead across every dependency point; the prefetch buffer must
    hold what the stacks deliver during the longest interval in which the core
    consumes no weights (the non-matrix stages between two weight ops of the
    spec chain), and the MAC rate must exceed the stream so the buffer drains."""
    bw = HBM["stacks"] * HBM["stack_bytes_s"] * HBM["efficiency"]
    rows = out["dependency_chain"][f"{CTX_HEAD}/spec"]["stages"]
    gap = cur = 0
    for r in rows:
        if r["kind"] == "mv":
            gap, cur = max(gap, cur), 0
        else:
            cur += r["throughput"] + r["exposed_latency"]
    gap = max(gap, cur)
    res = {}
    for t in CONTEXTS:
        per = {}
        for f, r in out["hbm_comparator"][str(t)].items():
            per[f] = dict(tokens_s_target=round(0.95 * r["tokens_s"], 1), tokens_s_bound=r["tokens_s"],
                          mac_lanes_min=2 * r["lanes_needed_at_clock"])
        res[str(t)] = per
    return dict(stacks=HBM["stacks"], sustained_efficiency_min=HBM["efficiency"],
                address_map="refresh-aware: pseudo-channels interleaved at the stream's word size and refresh phases "
                            "staggered, so no weight op meets the same refresh on every channel",
                efficiency_measured_with_refresh=True,
                controller_queue_beats_per_pseudo_channel_min=512,
                controller_queue_basis="bandwidth x tRFC (350 ns) = ~350 beats; on the V4.1 HBM vehicle a "
                                       "refreshing channel's full 64-beat queue stalled the in-order stream for "
                                       "~tRFC (up to 15% of a token); neutral for Qwen3 (+0.1%)",
                refresh_policy="0.90 of RAW peak with refresh on: REFab (tRFC 350 ns / tREFI 3.9 us, 9.0% floor) "
                               "meets it as measured on the Qwen3 reduced vehicle (0.904 / 0.910 at 1 / 2 pseudo-"
                               "channels); REFpb is allowed only with a record showing >= 0.90; a refreshing "
                               "channel must not stall requests to other channels",
                longest_weight_free_interval_cycles=gap,
                prefetch_buffer_bytes_min=math.ceil(bw * gap / clock),
                hbm_bytes_per_cycle=round(bw / clock), per_context=res,
                note="95% of the byte bound: the stream stalls only at the token start (the first weights' latency)")


def gap_table(out):
    req = out["requirements"]
    ab = out["baseline_as_built"]["as_built_calibrated"]["2048"]
    head = out["as_built_calibrated"][str(CTX_HEAD)]
    wsum = ab["unit_busy"].get("weights", 0) + ab["unit_busy"].get("lm_head", 0)
    hb = head["unit_busy"]
    return [
        dict(block="stream unit", requirement=f"{req['stream_unit_elements_per_cycle']['requirement']} elements/cycle",
             as_built=f"vector stream unit, SW lanes (landed: RTL parameter; {SPEC_SU_WIDTH} at the spec), "
                      "R-ARITH reducer", cycles_baseline_2k=ab["unit_busy"].get("stream", 0),
             cycles_head_8k=hb.get("stream", 0), status="MEETS"),
        dict(block="attention P.V", requirement="K-split over positions across every free group",
             as_built="interleaved K-split over positions (landed)", cycles_baseline_2k=ab["unit_busy"].get("attn_pv", 0),
             cycles_head_8k=hb.get("attn_pv", 0), status="MEETS"),
        dict(block="attention Q.K", requirement="K-split over head_dim across free groups",
             as_built="interleaved K-split over head_dim (landed)",
             cycles_baseline_2k=ab["unit_busy"].get("attn_scores", 0), cycles_head_8k=hb.get("attn_scores", 0),
             status="MEETS"),
        dict(block="dependency handling",
             requirement=f"<= {req['exposed_latency_per_dependent_stage_max']['requirement']} cycles exposed a stage",
             as_built="per-unit waits (landed: wait_me / wait_su, barrier = both), element chaining across "
                      "units; still whole-op granular within a unit",
             cycles_baseline_2k=ab["sequencer_stalls"].get("barrier_me", 0) + ab["sequencer_stalls"].get("barrier_su", 0),
             cycles_head_8k=sum(v for k2, v in head["sequencer_stalls"].items() if k2 != "unit_busy"),
             status="MISS"),
        dict(block="softmax", requirement="one stream-unit pass over the scores, 1/Z beside P.V",
             as_built="landed: the row max on the engine's result path (me_rmax), one exp pass, "
                      "normalise-after-sum (1/Z on 32 x 128 beside P.V), P.V chasing the exp pass by rows",
             cycles_baseline_2k=None, cycles_head_8k=None, status="MEETS"),
        dict(block="sequencer issue", requirement=req["instruction_issue"]["requirement"],
             as_built=f"prefetched issue pipeline: {head['instructions']} instructions at gap {T.K['seq_gap']} (landed)",
             cycles_baseline_2k=ab["seq_gap_total"], cycles_head_8k=head["seq_gap_total"], status="MEETS"),
        dict(block="matrix engine (weights)", requirement=req["weight_tiling_efficiency"]["requirement"] +
             f"; {GROUPS_ROM} groups and a 4-bit K-split field",
             as_built="4-bit me_split (landed); the reticle's groups are the RTL parameter G",
             cycles_baseline_2k=wsum, cycles_head_8k=hb.get("weights", 0) + hb.get("lm_head", 0), status="MEETS"),
        dict(block="KV in HBM (ROM die)", requirement=f"{ROM_KV_HBM['stacks']} stacks, "
                                                     f"{req['kv_hbm']['bytes_per_token'] / 1e6:.0f} MB/token FP8 KV, "
                                                     "streamed with prefetch",
             as_built="KV streamer (ot_hdc_kv_stream) exists for the unsplit attention order; BF16 KV only",
             cycles_baseline_2k=None, cycles_head_8k=req["kv_hbm"]["stream_cycles"], status="MISS"),
    ]


DRAFTER_PARAMS = 1_048_626_432     # z-lab/Qwen3-8B-DFlash-b16 safetensors header (BF16, all its own)
DRAFTER_LAYERS = 5
DFLASH_FC = (4096, 5 * 4096)
TAU_CENTRAL = 4.1                  # user decision: the pooled measured tau (561 blocks); 5.18 (mean of prompts) is a band


# Pooled acceptance lengths (tokens a step, accepted drafts + 1) of DFlash-b16
# on Qwen3-8B, fp32 torch reference, 6 prompts x 512 tokens, 561 blocks:
# results/speculative/dflash_validation_parts/reference_fp32.json at
# worktree-agent-a5d8c1340cfb92fbc 0b576189 (pooled tau 4.10; mean of prompts 5.18).
ACCEPT_HIST = {1: 169, 2: 118, 3: 79, 4: 51, 5: 29, 6: 13, 7: 12, 8: 9, 9: 14, 10: 9, 11: 5, 12: 3, 13: 3,
               14: 9, 15: 4, 16: 34}


def tokens_per_step(B):
    n = sum(ACCEPT_HIST.values())
    return sum(min(k, B) * v for k, v in ACCEPT_HIST.items()) / n


def rom_block_sweep(out, clock, ctx, fmt, m):
    """ROM speculative configurations: block B = 2..16 (B-1 drafts, B verified
    slots), tokens a step E[min(L, B)] from the measured block-16 acceptance
    lengths (a smaller block keeps the first B-1 drafts -- an approximation:
    DFlash drafts the block jointly).  The verify is KV-shared and
    slot-parallel (rom_token with B slots); the drafter's 5 layers over B
    slots, the target lm_head over B-1 and the context projection of B slots
    add their MACs (their latency overlapped); the KV stream carries the
    target's and the drafter's KV once a step."""
    per_layer, _ = matrices()
    layer_macs = sum(a * b for a, b in per_layer.values())
    head_macs = Q["V"] * Q["H"]
    plain, _, _ = rom_token(out, ctx, fmt)
    rows = []
    for B in (1, 2, 3, 4, 5, 6, 8, 12, 16):
        tok = tokens_per_step(B)
        if B == 1:
            step = plain
        else:
            _, comp, kv = rom_token(out, ctx, fmt, slots=B, m=m, drafter=True)
            draft_macs = B * DRAFTER_LAYERS * layer_macs + (B - 1) * head_macs + \
                B * (DFLASH_FC[0] * DFLASH_FC[1] + DRAFTER_LAYERS * 2 * Q["KV"] * Q["HD"] * Q["H"]) + \
                B * DRAFTER_LAYERS * 2 * Q["NH"] * Q["HD"] * (ctx + B)
            step = max(comp + draft_macs / (LANES_ROM * min(m, B)), kv)
        rows.append(dict(block=B, tokens_per_step=round(tok, 3), step_cycles=round(step),
                         tokens_s=round(tok * clock / step, 1), speedup=round(tok * plain / step, 3)))
    return rows


def dflash_budget(out, clock):
    """DFlash at the design point and at 2k, m = 1 and the area ledger's m.
    On the ROM reticle the MACs of every slot are real work; with KV in HBM the
    verify's slots share the KV stream, so speculation now amortises the KV
    term.  On the HBM comparator the BYTES bind, and m = 16 reads each weight
    once for 16 slots."""
    m_max = out["area"]["lane_multiplier_m"]
    rom = {}
    for ctx in CONTEXTS:
        for m in sorted({1, m_max}):
            key = f"{ctx}/{KV_FMT_SPEC}/m{m}"
            sweep = rom_block_sweep(out, clock, ctx, KV_FMT_SPEC, m)
            best = max(sweep, key=lambda r: r["tokens_s"])
            rom[key] = dict(context=ctx, kv_format=KV_FMT_SPEC, lane_multiplier=m, sweep=sweep, best=best)
    wl = out["workload"][str(CTX_HEAD)]
    bw = HBM["stacks"] * HBM["stack_bytes_s"] * HBM["efficiency"]
    per_layer, _ = matrices()
    layer_macs = sum(a * b for a, b in per_layer.values())
    n = DFLASH_SLOTS
    step_macs = n * DRAFTER_LAYERS * layer_macs + (n - 1) * Q["V"] * Q["H"] + n * (Q["L"] * layer_macs + Q["V"] * Q["H"]) \
        + n * wl["attention_macs"]
    hbm = {}
    for fmt, bpp in (("bf16", 2), ("fp8", 1), ("rom_format_3.5b", 3.5 / 8)):
        wbytes = (wl["weight_macs"] + DRAFTER_PARAMS) * bpp
        kvb = kv_bytes(wl, KV_FMT_SPEC) * (1 + DRAFTER_LAYERS / Q["L"])
        step_s = (wbytes + kvb) / bw
        plain_s = (wl["weight_macs"] * bpp + kv_bytes(wl, KV_FMT_SPEC)) / bw
        hbm[fmt] = dict(context=CTX_HEAD, step_s=step_s, plain_token_s=plain_s, tokens_s_plain=round(1 / plain_s, 1),
                        tokens_s_at_tau_central=round(TAU_CENTRAL / step_s, 1),
                        speedup_at_tau_central=round(TAU_CENTRAL * plain_s / step_s, 2),
                        mac_lanes_min=math.ceil(step_macs / (step_s * clock)))
    return dict(tau_central=TAU_CENTRAL, drafter_parameters=DRAFTER_PARAMS, rom=rom, hbm=hbm,
                requirements=["lane multiplier m (one weight or KV word feeds m slots); HBM m = 16",
                              "KV-shared verify attention: one K/V read serves every slot, the causal mask per slot",
                              "slot-parallel non-weight work: one op over all slots (the stream unit's lanes take "
                              "slots), never serial ops",
                              "16 DYN banks (token, pos + j); CTL TOKX/AMAX/DYN/ACCEPT/END; the shared accept unit",
                              "KV ring >= 17 entries; rollback is a commit pointer"])


BATCHES = (1, 2, 4, 8, 16, 32, 64, 128)
# Energy basis: the measured reduced Qwen3 step on the routed ASAP7 core
# (docs/ARCHITECTURE_ATLAS.html 8.7, signoff/energy_per_token.json).
E_LOGIC_PER_MAC = 16.5e-12       # whole step (upper: a tiny vehicle's clock and registers)
E_ME_PER_MAC = 3.97e-12           # the matrix engine alone (lower)
E_SRAM_PER_BYTE = 2.6e-12
E_HBM_PER_BYTE = 1.0488e-10
E_ROM_PER_BYTE = 8e-14
LEAK_W_ROM = RETICLE["rom_mm2"] * 0.0067


def batch_model(out, clock):
    """Batch B users decoding together at the design point (8k, FP8 KV) and at
    2k.  ROM reticle: the users share the chain's latency and the weight words
    (lane copies m divide the weight MACs), each has its own attention and KV
    stream: step = max(latency + ceil(B/m) x weights + B x (attention +
    elementwise), B x KV bytes / bandwidth).  KV in HBM: capacity is no longer
    a limit (6 x 24 GB).  HBM comparator: one weight read serves the batch:
    step = max((weights + B x KV) / bandwidth, B x MACs / lanes, latency)."""
    m = out["area"]["lane_multiplier_m"]
    res = {}
    for ctx in CONTEXTS:
        wl = out["workload"][str(ctx)]
        macs = wl["weight_macs"] + wl["attention_macs"]
        rom = []
        for mm in sorted({1, m}):
            for B in BATCHES:
                step, comp, kv = rom_token(out, ctx, KV_FMT_SPEC, users=B, m=mm)
                t = step / clock
                kvb = kv_bytes(wl, KV_FMT_SPEC)
                mem = wl["bytes"]["weights_rom_format"] * E_ROM_PER_BYTE + kvb * E_HBM_PER_BYTE
                e_hi = B * (macs * E_LOGIC_PER_MAC + mem) + LEAK_W_ROM * t
                e_lo = B * (macs * E_ME_PER_MAC + mem) + LEAK_W_ROM * t
                rom.append(dict(lane_multiplier=mm, batch=B, step_cycles=round(step),
                                per_user_tokens_s=round(clock / step, 1), total_tokens_s=round(B * clock / step, 1),
                                binding="kv_stream" if kv > comp else "compute",
                                energy_per_token_mj=round(e_hi / B * 1e3, 2),
                                energy_per_token_mj_matrix_engine_only=round(e_lo / B * 1e3, 2)))
        bw = HBM["stacks"] * HBM["stack_bytes_s"] * HBM["efficiency"]
        comp = out["dependency_chain"][f"{ctx}/spec"]["components"]
        lat = comp["latency"] + comp["control"]
        hbm = {}
        for fmt, bpp in (("bf16", 2), ("fp8", 1), ("rom_format_3.5b", 3.5 / 8)):
            rows = []
            for B in BATCHES:
                byt = wl["weight_macs"] * bpp + B * kv_bytes(wl, KV_FMT_SPEC)
                t = max(byt / bw, B * macs / (LANES_HBM * clock), lat / clock)
                e_hi = B * macs * E_LOGIC_PER_MAC + byt * E_HBM_PER_BYTE
                e_lo = B * macs * E_ME_PER_MAC + byt * E_HBM_PER_BYTE
                rows.append(dict(batch=B, step_cycles=round(t * clock), per_user_tokens_s=round(1 / t, 1),
                                 total_tokens_s=round(B / t, 1), energy_per_token_mj=round(e_hi / B * 1e3, 2),
                                 energy_per_token_mj_matrix_engine_only=round(e_lo / B * 1e3, 2),
                                 binding="bytes" if t == byt / bw else "macs" if t > lat / clock else "latency"))
            hbm[fmt] = rows
        res[str(ctx)] = dict(rom=rom, hbm=hbm, kv_format=KV_FMT_SPEC)
    return dict(per_context=res,
                note=f"HBM comparator rows at {LANES_HBM:,} lanes and the same KV format as the ROM die",
                lane_copies_serve_batch="yes: one weight word feeding m users' MACs is the DFlash lane multiplier",
                energy_basis="logic at the measured reduced step on the routed ASAP7 core: 16.5 pJ/MAC whole step "
                             "(upper), 3.97 pJ/MAC the matrix engine alone (lower); ROM 0.08 pJ/B, HBM 104.9 pJ/B, "
                             "ROM leakage 0.0067 W/mm2. Predictive PDK, upper-bound activity: an order-of-magnitude "
                             "figure, not a sign-off power")


COOLING_W = 408.0          # the reticle's cooling limit (iso-area study, worktree-agent-a57e0d89de203ba19 09b4b1b1)
HBM_IDLE_W_PER_STACK = 2.8  # idle interface power a stack (same study)
MAC_POWER_SHARE = 0.75     # of the die's cooling budget, to the MAC lanes (the rest: stream unit, control,
                           # clock, memories, PHY)
GPU_PJ_PER_MAC = 1.4       # SC'25 measured 0.70 pJ/FLOP (same study)


def power_budget(out, clock):
    """Power as a first-class requirement.  Die power = MAC rate x pJ/MAC +
    the rest of the logic; HBM DRAM energy is the stacks' own (reported, not
    charged to the die).  From the cooling limit and the design point's rate
    (and the best speculative configuration's MAC rate) follow the per-token
    energy budget and the pJ/MAC the matrix engine must reach.  Energy basis:
    ASAP7 sign-off of the reduced step (3.97 pJ/MAC the matrix engine, a
    BF16 x BF16 lane) used AS IS for the N6 reticle -- no node scaling."""
    wl = out["workload"][str(CTX_HEAD)]
    macs_tok = wl["weight_macs"] + wl["attention_macs"]
    target = out["budget"]["target_tokens_s"]
    m = out["area"]["lane_multiplier_m"]
    best = out["dflash"]["rom"][f"{CTX_HEAD}/{KV_FMT_SPEC}/m{m}"]["best"]
    B = best["block"]
    per_layer, _ = matrices()
    layer_macs = sum(a * b for a, b in per_layer.values())
    step_macs = B * macs_tok + B * DRAFTER_LAYERS * layer_macs + (B - 1) * Q["V"] * Q["H"] + \
        B * (DFLASH_FC[0] * DFLASH_FC[1])
    spec_mac_rate = step_macs * best["tokens_s"] / best["tokens_per_step"]
    ar_mac_rate = macs_tok * target
    mac_w = COOLING_W * MAC_POWER_SHARE - ROM_KV_HBM["stacks"] * HBM_IDLE_W_PER_STACK
    e_tok_budget = COOLING_W / target
    need_ar = mac_w / ar_mac_rate * 1e12
    need_spec = mac_w / spec_mac_rate * 1e12
    capped = {}
    for pj in (E_ME_PER_MAC * 1e12, GPU_PJ_PER_MAC):
        p_ar = ar_mac_rate * pj * 1e-12 / MAC_POWER_SHARE
        p_sp = spec_mac_rate * pj * 1e-12 / MAC_POWER_SHARE
        capped[f"{pj:.2f}_pj"] = dict(ar_die_w=round(p_ar, 1), ar_tokens_s_capped=round(min(target, target * COOLING_W / p_ar), 1),
                                     dflash_die_w=round(p_sp, 1),
                                     dflash_tokens_s_capped=round(min(best["tokens_s"], best["tokens_s"] * COOLING_W / p_sp), 1))
    kvb = kv_bytes(wl, KV_FMT_SPEC)
    return dict(cooling_limit_w=COOLING_W, mac_power_share=MAC_POWER_SHARE,
                energy_per_token_budget_mj=round(e_tok_budget * 1e3, 2),
                macs_per_token=macs_tok, ar_mac_rate_per_s=ar_mac_rate, dflash_best=dict(best, lane_multiplier=m),
                dflash_mac_rate_per_s=spec_mac_rate,
                pj_per_mac_required_ar=round(need_ar, 2), pj_per_mac_required_dflash=round(need_spec, 2),
                pj_per_mac_as_built_asap7=E_ME_PER_MAC * 1e12, pj_per_mac_gpu=GPU_PJ_PER_MAC,
                at=capped, hbm_dram_w_at_target=round(kvb * target * E_HBM_PER_BYTE, 1),
                node="energy is the ASAP7 (7 nm predictive) sign-off of the reduced step, applied unscaled to the N6 "
                     "reticle; N6 is the same node class, and no scaling factor is applied",
                mac_requirements=["the lane is designed for the ROM's weight format: 4-bit weights (3.5 bits a "
                                  "weight with group scales) x FP8/BF16 activations, FP32 accumulation -- not a "
                                  "BF16 x BF16 lane (a golden change: the quantised checkpoint)",
                                  "operand isolation and clock gating of idle lanes: groups outside an op's tiles, "
                                  "masked elements, idle lane copies",
                                  "accumulation width FP32 (the golden's order), products exact",
                                  f"<= {need_spec:.2f} pJ/MAC for the best speculative configuration uncapped; "
                                  f"<= {need_ar:.2f} for autoregressive decoding at the target"])


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    out = evaluate()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1, default=float) + "\n")
    UTIL_OUT.write_text(json.dumps(utilization(out, out["clock_hz"]), indent=1, default=float) + "\n")
    b = out["budget"]
    print(f"clock {out['clock_hz']/1e9:.4f} GHz; design point {CTX_HEAD} {KV_FMT_SPEC}: target {b['target_cycles']} "
          f"cycles = {b['target_tokens_s']} tok/s ({b['binding']}); weight ceiling {b['ceiling_tokens_s']}")
    print("area", out["area"])
    for k, v in out["rom_token"].items():
        print("rom token", k, v)
    for k, v in out["as_built_calibrated"].items():
        print(f"as built {k}: {v['cycles']} cycles")
    print(json.dumps(out["requirements"], indent=1)[:2500])


if __name__ == "__main__":
    main()
