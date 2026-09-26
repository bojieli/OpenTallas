#!/usr/bin/env python3
"""Top-down architecture budget of the Qwen3-8B decode core (docs/ARCH_SPEC_QWEN3.md).

    python3 tools/arch_budget_qwen3.py [--out results/arch/qwen3_budget.json]

Requirements first, then per-block specs: this model derives, from the model
graph alone, the per-token WORKLOAD (MACs by op class, bytes by storage level,
elementwise element-ops, reductions, the dependent-stage chain of a layer), the
per-resource ROOFLINE of the two Qwen3-8B designs

* ROM -- the single-reticle Taalas-HC1-class die (N6, 815 mm2) whose compute
  share (146.7 mm2) fixes 7,680 weight-lane groups = 122,880 BF16 MAC lanes;
  weights in ROM, KV in on-die SRAM;
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
MATVEC_PHYS = ROOT / "results/physical_abi3/asap7/hdc/ot_hdc_matvec/physical.json"
STREAM_PHYS = ROOT / "results/physical_abi3/asap7/hdc/ot_hdc_stream/physical.json"

Q = T.SHAPES["qwen3-8b"]
CONTEXTS = (2048, 8192)
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
ISA_MAX_SPLIT_AS_BUILT = 1 << ((1 << 2) - 1)    # me_split is 2 bits: S <= 8
HBM = dict(stacks=6, stack_bytes_s=1.0e12, efficiency=0.90, phy_mm2_per_stack=10.0,
           basis="HBM3E 1.0 TB/s a stack (B200: 8 TB/s over 8 stacks), 0.90 sustained "
                 "(configs/hardware/technology.json efficiencies.hbm_bandwidth); 6 stacks = the beachfront "
                 "of one reticle at 60% edge use and 12 mm a stack (H200 also carries 6)")
DFLASH_SLOTS = 16
SPEC_SU_WIDTH = 512               # the stream unit the spec sizes (requirements(): the one-pass softmax)


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


def roofline_rom(wl, clock, groups=GROUPS_ROM, su_width=SPEC_SU_WIDTH, kv_bytes_cycle=None):
    lanes = groups * W
    kvbc = kv_bytes_cycle or groups * W * 2          # one 16-lane BF16 word per group per cycle
    r = {"weights_mac": wl["weight_macs"] / lanes, "attention_mac": wl["attention_macs"] / lanes,
         "kv_sram_read": wl["bytes"]["kv_read"] / kvbc, "elementwise": wl["elementwise_total"] / su_width}
    return {k: dict(cycles=round(v), us=round(v / clock * 1e6, 3)) for k, v in r.items()}


def hbm_design(wl, clock, fmt):
    bw = HBM["stacks"] * HBM["stack_bytes_s"] * HBM["efficiency"]
    wbytes = {"bf16": wl["bytes"]["weights_bf16"], "fp8": wl["bytes"]["weights_fp8"],
              "rom_format_3.5b": wl["bytes"]["weights_rom_format"]}[fmt]
    t = (wbytes + wl["bytes"]["kv_read"]) / bw
    mac_rate = wl["weight_macs"] / t
    return dict(weight_format=fmt, bytes_per_token=wbytes + wl["bytes"]["kv_read"], sustained_bytes_s=bw,
                token_s=t, tokens_s=round(1 / t, 1), mac_rate_needed=mac_rate,
                lanes_needed_at_clock=math.ceil(mac_rate / clock),
                hbm_bytes_per_cycle=round(bw / clock))


# -- the budget ----------------------------------------------------------------------------
BUDGET_SHARES = dict(weights=0.55, attention=0.05, elementwise=0.07, latency=0.30, control=0.03)


def budget(wl2k, clock):
    """Target = the weight sweep at its tiling on the reticle's lanes over its
    share; every other resource gets the rest in fixed shares."""
    per_layer, head = matrices()
    w_cyc = Q["L"] * sum(mv_cycles(n, k, GROUPS_ROM)[0] for n, k in per_layer.values()) + \
        sum(mv_cycles(n, k, GROUPS_ROM)[0] for n, k in head.values())
    ideal = wl2k["weight_macs"] / LANES_ROM
    target = ideal / BUDGET_SHARES["weights"]
    alloc = {k: round(v * target) for k, v in BUDGET_SHARES.items()}
    return dict(weight_sweep_ideal_cycles=round(ideal), weight_sweep_tiled_cycles=w_cyc,
                weight_tiling_efficiency=round(ideal / w_cyc, 4), target_cycles=round(target),
                target_tokens_s=round(clock / target, 1), ceiling_tokens_s=round(clock / ideal, 1),
                shares=BUDGET_SHARES, cycles=alloc)


def requirements(wl, bud, clock):
    """Per-block requirements from the budget (2k context, batch 1)."""
    L, NH, HD, KV = Q["L"], Q["NH"], Q["HD"], Q["KV"]
    cyc = bud["cycles"]
    T_ctx = wl["context"]
    stages = len(LAYER_STAGES)
    # attention: MACs within its share -> lanes it must occupy
    attn_lanes = wl["attention_macs"] / cyc["attention"]
    kv_bpc = wl["bytes"]["kv_read"] / cyc["attention"]
    # elementwise within its share: the spec's one-pass softmax (max on the
    # engine's result path, 1/Z after P.V) leaves one pass over NH x T
    ew_spec = wl["elementwise_total"] - wl["elementwise"]["softmax"] + L * NH * T_ctx + L * NH * HD
    su = ew_spec / cyc["elementwise"]
    # the chain hides elementwise stages that chain into their consumer: the
    # width is the narrowest power of two whose EXPOSED elementwise cycles (the
    # reductions' passes) fit the share (scaled with the context at 8k)
    su_w = 1
    while su_w < 1 << 14 and any(
            L * chain(t, GROUPS_ROM, su_w, dict(AS_BUILT_LAT, seq_gap=1), "ksplit", True,
                      stages=LAYER_STAGES_SPEC)[1]["elementwise"] > cyc["elementwise"] * t / T_ctx
            for t in CONTEXTS):
        su_w *= 2
    stages = len(LAYER_STAGES_SPEC)
    lat_stage = cyc["latency"] / (L * stages)
    issue = cyc["control"]
    return dict(
        mac_lanes=dict(requirement=LANES_ROM, basis="the reticle's compute share (weights bind)"),
        weight_tiling_efficiency=dict(requirement=">= 0.90 of the ideal sweep (split/tile quantisation)"),
        rom_read_bytes_per_cycle=dict(requirement=round(LANES_ROM * RETICLE["weight_bits"] / 8),
                                      basis="one weight per lane per cycle at the ROM format"),
        attention_lanes_min=dict(requirement=math.ceil(attn_lanes),
                                 basis=f"{wl['attention_macs']:.3e} MACs in {cyc['attention']} cycles"),
        kv_read_bytes_per_cycle_min=dict(requirement=math.ceil(kv_bpc),
                                         basis="each K/V element once per token (GQA-shared) within the attention "
                                               "share; the RTL's per-group KV port gives groups x 32 B"),
        kv_sram_banks_min=dict(requirement=math.ceil(kv_bpc / (W * 2)), basis="16-lane BF16 words per bank per cycle"),
        kv_capacity_bytes=dict(requirement=wl["bytes"]["kv_capacity"],
                               sram_mm2=round(wl["bytes"]["kv_capacity"] * 8 / SRAM_BITS_PER_MM2, 1),
                               reticle_sram_mm2=RETICLE["sram_mm2"]),
        stream_unit_elements_per_cycle=dict(requirement=su_w, all_elements_unchained=round(su, 1),
                                            reference_graph_elements_per_cycle=round(
                                                wl["elementwise_total"] / cyc["elementwise"], 1),
                                            basis=f"the spec chain's exposed (unchained) elementwise cycles within "
                                                  f"{cyc['elementwise']} at 2k (scaled with the context at 8k); "
                                                  f"all {ew_spec:.3e} element-ops of the one-pass softmax graph "
                                                  f"unchained would need {round(su)}/cycle, and the reference "
                                                  f"graph's three softmax passes ({wl['elementwise_total']:.3e}) "
                                                  f"{round(wl['elementwise_total'] / cyc['elementwise'])}/cycle"),
        reduction_tree=dict(requirement=f"lane partials + a {int(math.log2(su_w))}-level cross-lane pairwise tree",
                            basis="a reduction of n elements on W lanes: n/W cycles + the tree"),
        exposed_latency_per_dependent_stage_max=dict(
            requirement=round(lat_stage), stages_per_layer=stages,
            basis=f"{cyc['latency']} cycles over {L} layers x {stages} dependent stages: tile-granular chaining, "
                  "never a full-unit drain"),
        instruction_issue=dict(requirement=f"<= {issue} control cycles a token exposed: issue back-to-back "
                                           "(prefetched decode), the next op queued while the unit runs",
                               per_instruction_max=round(issue / 4540, 2)),
        argmax=dict(requirement="streaming compare tree over each result word, no pass over the logits",
                    basis="151,936 logits emerge 128 a slot from the lm_head sweep"),
        vector_buffer=dict(requirement_elements=max(2 * Q["FF"], NH * T_ctx),
                           basis="gate/up outputs (2 x FF) and the score/probability rows (NH x T)"))


def capped_layout(groups, max_split):
    """tools/hdc_timing.ShapeLayout with every matrix's split capped (the ISA's
    me_split field) and tiled by the RTL's floor(G/S) rule."""
    lay = T.ShapeLayout(Q, groups)
    for key, m in lay.mat.items():
        s, rounds, kc = split_rounds(m["n"], m["k"] * m["split"], groups, max_split)
        m.update(k=kc, tiles=rounds, split=s)
    return lay


def as_built(T_ctx, groups=GROUPS_BUDGET, su_width=1, max_split=ISA_MAX_SPLIT_AS_BUILT):
    """The calibrated sequencer model replaying the decode program at the shipped
    shapes on the reticle's 7,680 groups with the ISA as built (split <= 8):
    cycles and their attribution (unit busy by class, sequencer stalls)."""
    import collections
    import hdc_program as P
    lay = capped_layout(groups, max_split)
    prog = P.build_program(lay)
    dyn = dict(H=Q["H"], half=Q["HD"] // 2, HD=Q["HD"])
    tr = []
    _, cyc = T.simulate(prog, T_ctx - 1, groups=groups, dyn_shape=dyn, su_width=su_width, trace=tr)
    d = T.dyn_values(T_ctx - 1, groups=groups, **dyn)
    busy = collections.Counter()
    stall = collections.Counter()
    for f, (why, g) in zip(prog, tr):
        f = {n: f.get(n, 0) for n, _ in I.FIELDS}
        if f["unit"] == I.UNIT_ME:
            c = "attn_scores" if f["me_wsrc"] and f["me_d_tiles"] else "attn_pv" if f["me_wsrc"] else \
                "lm_head" if f["me_amax"] else "weights"
            busy[c] += (f["me_tiles"] + d[f["me_d_tiles"]]) * (f["me_k"] + d[f["me_d_k"]]) * IL
        elif f["unit"] == I.UNIT_SU:
            busy["stream"] += -(-f["su_nout"] * (f["su_nin"] + d[f["su_d_nin"]]) // su_width)
        stall[why] += g
    n = sum(1 for f in prog if f.get("unit") != I.UNIT_END)
    return dict(context=T_ctx, groups=groups, su_width=su_width, max_split=max_split, instructions=n, cycles=cyc,
                unit_busy=dict(busy), sequencer_stalls={k: v for k, v in stall.items() if k != "issue"},
                seq_gap_total=n * T.K["seq_gap"])


def evaluate():
    clock = clock_hz()
    out = dict(schema=SCHEMA, tool="tools/arch_budget_qwen3.py", model="Qwen3-8B", shape=Q, clock_hz=clock,
               clock_basis="slowest routed Qwen3 token-path unit (ot_hdc_matvec, ot_hdc_stream; ASAP7 TT)",
               reticle=RETICLE, rom_design=dict(groups=GROUPS_ROM, lanes=LANES_ROM, mac_um2_asap7=MAC_UM2),
               hbm_design=HBM)
    out["workload"] = {str(t): workload(t) for t in CONTEXTS}
    wl2 = out["workload"]["2048"]
    out["roofline_rom"] = {str(t): roofline_rom(out["workload"][str(t)], clock) for t in CONTEXTS}
    out["hbm_comparator"] = {str(t): {f: hbm_design(out["workload"][str(t)], clock, f)
                                      for f in ("bf16", "fp8", "rom_format_3.5b")} for t in CONTEXTS}
    bud = budget(wl2, clock)
    out["budget"] = bud
    out["requirements"] = requirements(wl2, bud, clock)
    # dependent-stage chain: as built vs the spec
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
    out["as_built_calibrated"] = {str(t): as_built(t) for t in CONTEXTS}
    # the figure first reported (split uncapped: the 2-bit me_split field ignored)
    out["as_built_split_uncapped"] = as_built(2048, max_split=None)
    out["gap"] = gap_table(out)
    out["hbm_requirements"] = hbm_requirements(out, clock)
    # with DFlash: a 16-slot verify step reads every weight once for 16 slots
    out["dflash"] = dflash_budget(out, clock)
    return out


def hbm_requirements(out, clock):
    """The iso-area HBM comparator: the weight stream binds, so the design goal
    is a stream that never stalls.  Weights are data-independent, so the
    stream runs ahead across every dependency point; the prefetch buffer must
    hold what the stacks deliver during the longest interval in which the core
    consumes no weights (the non-matrix stages between two weight ops of the
    spec chain), and the MAC rate must exceed the stream so the buffer drains."""
    bw = HBM["stacks"] * HBM["stack_bytes_s"] * HBM["efficiency"]
    rows = out["dependency_chain"]["8192/spec"]["stages"]
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
                            "staggered, so no weight op meets the same refresh on every channel (the npc=8 refresh "
                            "alignment outlier of tools/rtl_hdc_hbm_campaign.py)",
                efficiency_measured_with_refresh=True,
                controller_queue_beats_per_pseudo_channel_min=512,
                controller_queue_basis="bandwidth x tRFC (350 ns) = ~350 beats; a refreshing channel's full queue "
                                       "stalled the in-order stream for ~tRFC (V4.1 HBM vehicle: up to 15% of a "
                                       "token with the 64-beat queue; 256 beats removes most of it)",
                refresh_policy="0.90 is of RAW peak with refresh on, so REFab (JESD238 tRFC 350 ns / tREFI 3.9 us: a "
                               "91.0% ceiling, measured 0.904 / 0.910 at 1 / 2 pseudo-channels on the Qwen3 reduced "
                               "vehicle) is not enough: refresh-aware REFpb (tRFCpb 200 ns) is required, and a "
                               "refreshing channel must not stall requests to other channels (no head-of-line "
                               "blocking); REFpb as modelled reaches 0.914 / 0.889 with a 512-beat queue -- open",
                longest_weight_free_interval_cycles=gap,
                prefetch_buffer_bytes_min=math.ceil(bw * gap / clock),
                hbm_bytes_per_cycle=round(bw / clock), per_context=res,
                note="95% of the byte bound: the stream stalls only at the token start (the first weights' latency)")


def gap_table(out):
    req = out["requirements"]
    ab = out["as_built_calibrated"]["2048"]
    wsum = ab["unit_busy"].get("weights", 0) + ab["unit_busy"].get("lm_head", 0)
    return [
        dict(block="stream unit", requirement=f"{req['stream_unit_elements_per_cycle']['requirement']} elements/cycle",
             as_built="1 element/cycle", cycles_as_built_2k=ab["unit_busy"].get("stream", 0), status="MISS"),
        dict(block="attention P.V", requirement="K-split over positions across every free group",
             as_built="head_dim on lanes (8 of 7,680 groups), positions in order: T x 8 cycles an op",
             cycles_as_built_2k=ab["unit_busy"].get("attn_pv", 0), status="MISS"),
        dict(block="attention Q.K", requirement="K-split over head_dim across free groups",
             as_built="positions on lanes (128 groups at 2k), head_dim in order: 1,024 cycles an op",
             cycles_as_built_2k=ab["unit_busy"].get("attn_scores", 0), status="MISS"),
        dict(block="dependency handling",
             requirement=f"<= {req['exposed_latency_per_dependent_stage_max']['requirement']} cycles exposed a stage",
             as_built="full-unit barrier drains (both units idle) on every region conflict",
             cycles_as_built_2k=ab["sequencer_stalls"].get("barrier_me", 0) + ab["sequencer_stalls"].get("barrier_su", 0),
             status="MISS"),
        dict(block="sequencer issue", requirement=req["instruction_issue"]["requirement"],
             as_built=f"{ab['instructions']} instructions at seq_gap {T.K['seq_gap']}",
             cycles_as_built_2k=ab["seq_gap_total"], status="MISS"),
        dict(block="matrix engine (weights)", requirement=req["weight_tiling_efficiency"]["requirement"] +
             f"; spec: {GROUPS_ROM} groups (a power of two) and a K-split field up to 2^13",
             as_built=f"2-bit me_split (S <= 8) on 7,680 groups: "
                      f"{out['budget']['weight_sweep_ideal_cycles'] * GROUPS_ROM / GROUPS_BUDGET / wsum:.2f} of ideal",
             cycles_as_built_2k=wsum, status="MISS"),
        dict(block="KV SRAM", requirement=f">= {req['kv_read_bytes_per_cycle_min']['requirement']} B/cycle, "
                                          f"{req['kv_capacity_bytes']['sram_mm2']} mm2 at 2k",
             as_built="one 16-lane word per group per cycle (up to 7,680 x 32 B)", cycles_as_built_2k=None,
             status="MEETS (ports) / capacity fits at 2k only"),
    ]


DRAFTER_PARAMS = 1_048_626_432     # z-lab/Qwen3-8B-DFlash-b16 safetensors header (BF16, all its own)
DRAFTER_LAYERS = 5
DFLASH_FC = (4096, 5 * 4096)
TAU_CENTRAL = 5.18                 # measured: fp32 torch reference, 6 prompts (DFlash agent, reference_fp32.json)


# Pooled acceptance lengths (tokens a step, accepted drafts + 1) of DFlash-b16
# on Qwen3-8B, fp32 torch reference, 6 prompts x 512 tokens, 561 blocks:
# results/speculative/dflash_validation_parts/reference_fp32.json at
# worktree-agent-a5d8c1340cfb92fbc 0b576189 (pooled tau 4.10; mean of prompts 5.18).
ACCEPT_HIST = {1: 169, 2: 118, 3: 79, 4: 51, 5: 29, 6: 13, 7: 12, 8: 9, 9: 14, 10: 9, 11: 5, 12: 3, 13: 3,
               14: 9, 15: 4, 16: 34}


def rom_block_sweep(out, clock):
    """ROM speculative configurations at the spec's lanes: block B = 2..16 (B-1
    drafts, B verified slots), tokens a step E[min(L, B)] from the measured
    block-16 acceptance lengths (a smaller block keeps the first B-1 drafts --
    an approximation: DFlash drafts the block jointly), KV-shared slot-parallel
    verify (the step's dependency latency is one plain token's, its MACs B
    tokens'), the drafter's 5 layers over B slots and the target lm_head over
    B-1, the context projection of B slots.  'overlapped' hides the drafter's
    dependency latency under the verify (the MACs cannot overlap: they bind)."""
    ch = out["dependency_chain"]["2048/spec"]
    comp = ch["components"]
    lat = comp["latency"] + comp["control"]
    per_layer, _ = matrices()
    layer_macs = sum(a * b for a, b in per_layer.values())
    head_macs = Q["V"] * Q["H"]
    wl = out["workload"]["2048"]
    n_blocks = sum(ACCEPT_HIST.values())
    rows = []
    for B in (2, 3, 4, 5, 6, 8, 12, 16):
        tok = sum(min(k, B) * v for k, v in ACCEPT_HIST.items()) / n_blocks
        verify = B * (comp["weights"] + comp["attention"] + comp["elementwise"])
        draft_macs = B * DRAFTER_LAYERS * layer_macs + (B - 1) * head_macs + \
            B * (DFLASH_FC[0] * DFLASH_FC[1] + DRAFTER_LAYERS * 2 * Q["KV"] * Q["HD"] * Q["H"]) + \
            B * DRAFTER_LAYERS * 2 * Q["NH"] * Q["HD"] * (wl["context"] + B)
        draft_lat = lat * DRAFTER_LAYERS / Q["L"]
        serial = lat + verify + draft_macs / LANES_ROM + draft_lat
        overl = lat + verify + draft_macs / LANES_ROM
        rows.append(dict(block=B, tokens_per_step=round(tok, 3), step_cycles=round(serial),
                         step_cycles_overlapped=round(overl), tokens_s=round(tok * clock / serial, 1),
                         tokens_s_overlapped=round(tok * clock / overl, 1)))
    return rows


def dflash_budget(out, clock):
    """One DFlash step (block 16): DRAFT (the drafter's 5 layers over 16 slots
    and the target's lm_head over 15), VERIFY (the target over 16 slots,
    causal), CONTEXT (fc and the drafter's k/v projections of 16 slots).  Every
    MAC of a slot is real work: one weight word read can feed m slots (the lane
    multiplier), but on the ROM reticle the MAC LANES bind, and 16 slots need
    16x the MACs whatever m is, unless lanes are added.  On the HBM comparator
    the BYTES bind, and m = 16 reads each weight once for 16 slots."""
    wl = out["workload"]["2048"]
    n = DFLASH_SLOTS
    L = Q["L"]
    per_layer, _ = matrices()
    layer_macs = sum(a * b for a, b in per_layer.values())
    head_macs = Q["V"] * Q["H"]
    kvproj = 2 * Q["KV"] * Q["HD"] * Q["H"]
    draft = n * DRAFTER_LAYERS * layer_macs + (n - 1) * head_macs
    verify = n * (L * layer_macs + head_macs)
    context = n * (DFLASH_FC[0] * DFLASH_FC[1] + DRAFTER_LAYERS * kvproj)
    attn_verify = n * wl["attention_macs"]
    attn_draft = n * DRAFTER_LAYERS * 2 * Q["NH"] * Q["HD"] * (wl["context"] + n)
    step_macs = draft + verify + context + attn_verify + attn_draft
    plain = out["dependency_chain"]["2048/spec"]["token_cycles"]
    floor = step_macs / LANES_ROM
    spare = RETICLE["sram_mm2"] - out["requirements"]["kv_capacity_bytes"]["sram_mm2"] - \
        DRAFTER_PARAMS / 8.190735e9 * RETICLE["rom_mm2"]
    copies = int(spare / (LANES_ROM * MAC_UM2 * 1e-6))
    rom = dict(step_mac_floor_cycles=round(floor), plain_token_cycles_spec=plain,
               breakeven_tau=round(floor / plain, 2),
               tokens_s_at_tau_central=round(TAU_CENTRAL * clock / floor, 1),
               plain_tokens_s_spec=round(clock / plain, 1),
               drafter_rom_mm2_3p5b=round(DRAFTER_PARAMS / 8.190735e9 * RETICLE["rom_mm2"], 1),
               spare_sram_mm2_after_kv_2k_and_drafter=round(spare, 1),
               added_lane_copies_that_fit=copies,
               tokens_s_at_tau_central_with_added_copies=round(TAU_CENTRAL * clock / (floor / (1 + copies)), 1)
               if copies else None,
               verdict="the ROM reticle is MAC-bound: a 16-slot step needs 16x a plain token's MACs, so at the "
                       "spec's lanes speculation pays only while the plain token stays above breakeven_tau x its "
                       "MAC floor; lane copies (m) taken from spare SRAM are the lever, a first-class area trade "
                       "against the KV/SRAM budget")
    bw = HBM["stacks"] * HBM["stack_bytes_s"] * HBM["efficiency"]
    res = {}
    for fmt, bpp in (("bf16", 2), ("fp8", 1), ("rom_format_3.5b", 3.5 / 8)):
        wbytes = (wl["weight_macs"] + DRAFTER_PARAMS) * bpp
        kvb = wl["bytes"]["kv_read"] * (1 + DRAFTER_LAYERS / L)
        step_s = (wbytes + kvb) / bw                    # KV-shared: one KV read serves the 16 slots
        plain_s = (wl["weight_macs"] * bpp + wl["bytes"]["kv_read"]) / bw
        lanes = math.ceil(step_macs / (step_s * clock))
        res[fmt] = dict(step_s=step_s, plain_token_s=plain_s, tokens_s_plain=round(1 / plain_s, 1),
                        tokens_s_at_tau_central=round(TAU_CENTRAL / step_s, 1),
                        speedup_at_tau_central=round(TAU_CENTRAL * plain_s / step_s, 2),
                        mac_lanes_min=lanes)
    rom["block_size_sweep"] = rom_block_sweep(out, clock)
    best = max(rom["block_size_sweep"], key=lambda r: r["tokens_s_overlapped"])
    rom["best_configuration"] = dict(best, plain_tokens_s_spec=rom["plain_tokens_s_spec"],
                                     speedup=round(best["tokens_s_overlapped"] / rom["plain_tokens_s_spec"], 3))
    return dict(slots=n, tau_central=TAU_CENTRAL, drafter_parameters=DRAFTER_PARAMS,
                macs=dict(draft=draft, verify=verify, context=context, attention_verify=attn_verify,
                          attention_draft=attn_draft, step=step_macs),
                rom=rom, hbm=res,
                requirements=["lane multiplier m (one weight word feeds m slots); HBM m = 16",
                              "KV-shared verify attention: one K/V read serves 16 slots, the causal mask per slot",
                              "slot-parallel non-weight work: one op over all 16 slots (the stream unit's lanes "
                              "take slots), never 16 serial ops",
                              "16 DYN banks (token, pos + j); CTL TOKX/AMAX/DYN/ACCEPT/END; the shared accept unit",
                              "KV ring >= 17 entries; rollback is a commit pointer"])


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    out = evaluate()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1, default=float) + "\n")
    b = out["budget"]
    print(f"clock {out['clock_hz']/1e9:.4f} GHz; weight sweep ideal {b['weight_sweep_ideal_cycles']} cycles "
          f"(ceiling {b['ceiling_tokens_s']} tok/s), tiled {b['weight_sweep_tiled_cycles']}; "
          f"target {b['target_cycles']} cycles = {b['target_tokens_s']} tok/s")
    for k, v in out["dependency_chain"].items():
        print(f"chain {k}: {v['token_cycles']} cycles ({v['tokens_s']} tok/s) {v['components']}")
    for k, v in out["as_built_calibrated"].items():
        print(f"as built {k}: {v['cycles']} cycles")
    for k, v in out["hbm_comparator"].items():
        print(f"hbm {k}: " + ", ".join(f"{f} {r['tokens_s']} tok/s ({r['lanes_needed_at_clock']} lanes)" for f, r in v.items()))
    print(json.dumps(out["requirements"], indent=1)[:3000])
    print(json.dumps({k: v for k, v in out["dflash"].items() if k != "requirements"}, indent=1))
    print(json.dumps(out["hbm_requirements"], indent=1))


if __name__ == "__main__":
    main()
