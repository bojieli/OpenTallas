#!/usr/bin/env python3
"""Qwen3-8B at O4: per-block performance requirements, the INT8 numerics check and the RTL gap audit.

    python3 tools/qwen3_o4_rtl_gaps.py [--out results/arch/qwen3_o4_rtl_gaps.json] [--rows 192]

ADVISORY INPUT to the two-reticle RTL contract (Codex's Qwen agent owns the contract and the integration).  It
prescribes no interface; it states what each block must sustain for the O4 rates, what the current RTL assumes,
and the numerics the 8-bit weight path must reproduce.  Read with docs/ARCH_QWEN3_O4_RTL_SPEC.md.

O4 (user decision 2026-09-28, TASKS.md section 1): two reticles in one package, INT8 weight-only (signed,
symmetric, one BF16 scale per output channel, never 4-bit), every layer split across the two dies over UCIe
(tensor-parallel 2), 4 HBM3E stacks a die, 6,144 lane groups a die (ROM-read bound), lane multiplier m = 5 for the
DFlash verify (block 5).  Its rates come from the O4 record, results/arch/qwen3_8bit_design.json on
claude/qwen-o4 @ 58d70929 (not on main when this was written), carried below as O4 and re-checked against the
file when it is present.

1. REQUIREMENTS: per die, per layer and per token, for the autoregressive gate (m = 1, B = 1) and the DFlash
   verify gate (m = 5, B = 5): ROM read, matrix-engine cycles, attention, stream-unit work, KV bytes and
   bandwidth, the scale multiply's throughput, the UCIe exchanges (bytes, latency, buffering) -- derived here
   from the shapes (tools/hdc_timing.SHAPES), the engine's tiling rule (tools/arch_budget_qwen3.split_rounds, the
   rtl/hdc/ot_hdc_matvec.sv rule), configs/hardware/technology.json links.rom_package_ucie and the O4 record.
2. NUMERICS: signed INT8 codes x BF16 activations, FP32 accumulation in the golden's K-split order, one
   FP32 x BF16 scale multiply per output row after accumulation (the contract), against the quality harness's
   quantised arithmetic (tools/qwen3_deployment_quality.py: its quantiser at 8 bits with one group per row, and
   its chunk-tree kernel, which applies the scale inside every product), on real Qwen3-8B rows when the HF
   snapshot is on disk, else on synthetic rows.  Also: the INT8 x BF16 product is exact in FP32, the INT8 code is
   exact in BF16, the embedding dequantisation is exact, and the two orders of the scale around the TP fold.
3. GAPS: block -> current RTL -> required -> change size -> owner.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import hdc_golden as G  # noqa: E402

SCHEMA = "opentallas.qwen3-o4-rtl-gaps.v1"
OUT = ROOT / "results/arch/qwen3_o4_rtl_gaps.json"
DOC = ROOT / "docs/ARCH_QWEN3_O4_RTL_SPEC.md"
TECH = ROOT / "configs/hardware/technology.json"
O4_FILE = ROOT / "results/arch/qwen3_8bit_design.json"

# tools/hdc_timing.SHAPES["qwen3-8b"] (= configs/models/qwen3-8b.json)
Q = dict(H=4096, L=36, NH=32, KV=8, HD=128, FF=12288, V=151936)
W, IL = 16, 8                        # lanes a group, outputs in flight a lane (rtl/hdc/ot_hdc_matvec.sv)
DIES, TP = 2, 2
GROUPS_DIE = 6144
STACKS_DIE = 4
STACK_BYTES_S, HBM_EFF = 1.0e12, 0.90          # tools/arch_budget_qwen3.HBM
T_RFC_S = 350e-9                                # tools/arch_budget_qwen3.T_RFC_S
CTX = 8192
KV_BYTES = 1                                    # FP8 E4M3 KV (the golden's kv_round on the vector core)
SU_WIDTH = 1024                                 # tools/arch_budget_qwen3.SPEC_SU_WIDTH
DRAFTER_LAYERS = 5                              # tools/dflash_step_timing
DFLASH_FC = (4096, 5 * 4096)
DFLASH_TAP_LAYERS = 5                           # target hidden states the drafter's fc reads (layers 1,9,17,25,33)
REDUCE_ADD_CYCLES = 4                           # tools/qwen3_8bit_design.REDUCE_ADD_CYCLES
FP32_MUL_LAT = 4                                # ASSUMED depth of the post-accumulation scale multiply pipe

# The O4 record (claude/qwen-o4 @ 58d70929, results/arch/qwen3_8bit_design.json,
# configurations.O4_two_reticles_one_package), the figures this audit budgets against.
O4 = dict(
    source="results/arch/qwen3_8bit_design.json @ claude/qwen-o4 58d70929, configurations.O4_two_reticles_one_package",
    clock_hz=1098640000.0,
    groups_per_die=6144, lanes_per_die=98304, lane_multiplier_m=5, lane_copies_added=4, lane_copy_mm2=51.91,
    target_rom_mm2=224.65, drafter_rom_mm2=28.76, ucie_phy_mm2=10.0, kv_ring_mm2=6.2, slack_mm2=28.21,
    rom_read_required_bytes_per_cycle_per_die=98304, rom_read_headroom=1.017,
    weight_sweep_ideal_cycles=38493, weight_sweep_tiled_cycles=38880,
    kv_bytes_per_token=603979776.0, kv_floor_cycles=92161,
    calibrated_chain_cycles=104473, extra_chain_cycles=1251, ar_step_cycles=105724, ar_tokens_s=10391.6,
    ar_binding="compute_chain", spec_chain_cycles=122652, plain_cycles=123903,
    dflash_block=5, tokens_per_step=2.8591, step_cycles=189758, draft_cycles=26677, verify_cycles=163071,
    commit_cycles=10, dflash_tokens_s=16553.3, speedup_over_plain=1.867,
    spec_components=dict(weights=38880, attention=16128, elementwise=9792, latency=57132, control=720),
    # tools/arch_budget_qwen3.as_built(8192, groups=12288) at claude/qwen-o4: the TP pair as one engine
    as_built=dict(cycles=104473, unit_busy=dict(stream=21177, weights=35712, attn_scores=9216, attn_pv=9216,
                                                lm_head=3168),
                  layer_chain_cycles=2807,
                  layer_stages=[("QKV projection, then q/k norm, RoPE", 564, 128),
                                ("attention: scores, softmax, P.V, 1/Z", 873, 512),
                                ("O projection, residual, FFN norm", 183, 88),
                                ("gate/up projection, fused SiLU.up", 828, 512),
                                ("down projection, residual, next norm", 359, 264)]),
    as_built_6144_one_die_cycles=160881,     # as_built(8192, groups=6144): one die's engine, all 36 layers
    power_b_die_w_ar=419.9, power_b_die_w_dflash=417.4, cooling_die_limit_w_air=374.6,
    capacity=dict(target_scales=1400832, lm_head_scales=151936, embedding_scales=151936, drafter_scales=198656,
                  target_elements=6945767424, lm_head_elements=622329856, embedding_elements=622329856,
                  drafter_elements=1048576000),
)


# -- 1. requirements ------------------------------------------------------------------------------------------------
def split_rounds(n, k, groups):
    """(S, rounds, K/S) under the RTL's tiling rule (rtl/hdc/ot_hdc_matvec.sv; tools/arch_budget_qwen3.split_rounds):
    S = 2^i contiguous K chunks, floor(G/S) tiles of W x IL rows a round, fewest cycles, smaller S on a tie."""
    tiles = -(-n // (W * IL))
    best = None
    s = 1
    while s <= groups:
        if k % s == 0 and groups // s >= 1:
            rounds = -(-tiles // (groups // s))
            c = rounds * (k // s) * IL
            if best is None or c < best[0]:
                best = (c, s, rounds)
        s *= 2
    return best[1], best[2], k // best[1]


def mv_cycles(n, k, groups):
    s, rounds, kc = split_rounds(n, k, groups)
    return rounds * kc * IL


def die_matrices():
    """Each die's slice of every matrix (Megatron TP-2, tools/hdc_golden.Model.die_slices): QKV and gate/up split by
    output rows (heads, FFN rows), o and down by input columns (partials all-reduced), lm_head by vocabulary."""
    H, NH, KV, HD, FF, V = (Q[k] for k in ("H", "NH", "KV", "HD", "FF", "V"))
    return {"qkv": ((NH + 2 * KV) * HD // TP, H), "o": (H, NH * HD // TP), "gate_up": (2 * FF // TP, H),
            "down": (H, FF // TP)}, {"lm_head": (V // TP, H)}


def link():
    L = json.loads(TECH.read_text())["links"]["rom_package_ucie"]
    return dict(bytes_s=L["bytes_s"]["value"], hop_s=L["hop_latency_s"]["value"],
                hop_s_low=L["hop_latency_s"]["range_low"], hop_s_high=L["hop_latency_s"]["range_high"])


def requirements():
    clk = O4["clock_hz"]
    lanes = GROUPS_DIE * W
    per_layer, head = die_matrices()
    mats = {}
    for name, (n, k) in {**per_layer, **head}.items():
        s, rounds, kc = split_rounds(n, k, GROUPS_DIE)
        cyc = rounds * kc * IL
        mats[name] = dict(n=n, k=k, split=s, rounds=rounds, k_chunk=kc, cycles=cyc,
                          weight_bytes_int8=n * k, scales=n,
                          outputs_per_cycle_avg=round(n / cyc, 2),
                          burst_outputs_per_cycle=(GROUPS_DIE // s) * W)
    layer_mv = sum(mats[k]["cycles"] for k in per_layer)
    layer_w_bytes = sum(mats[k]["weight_bytes_int8"] for k in per_layer)
    token_w_bytes = Q["L"] * layer_w_bytes + mats["lm_head"]["weight_bytes_int8"]
    rom_bpc = lanes * 8 // 8                               # one INT8 weight a lane a cycle
    scale_bytes_die = (O4["capacity"]["target_scales"] + O4["capacity"]["lm_head_scales"]
                       + O4["capacity"]["embedding_scales"] + O4["capacity"]["drafter_scales"]) * 2 // TP
    # KV: each die holds and streams its 4 KV heads (die_heads: 16 query heads, 4 KV heads)
    kv_heads_die = Q["KV"] // TP
    kv_layer_die = 2 * kv_heads_die * Q["HD"] * CTX * KV_BYTES
    kv_bw_die = STACKS_DIE * STACK_BYTES_S * HBM_EFF
    kv_bpc_die = kv_bw_die / clk
    kv_layer_cycles = kv_layer_die / kv_bpc_die
    ring_die = kv_layer_die + kv_bw_die * T_RFC_S
    # attention MACs a die a layer at 8K (scores + P.V, its 16 query heads)
    attn_macs_layer_die = 2 * (Q["NH"] // TP) * Q["HD"] * CTX
    # UCIe exchanges (FP32 partials: tools/hdc_golden.fold adds FP32 matvec outputs)
    lk = link()
    ex_bytes = Q["H"] * 4
    hop_c = lk["hop_s"] * clk
    xfer_c = ex_bytes / lk["bytes_s"] * clk
    per_ex = hop_c + xfer_c + REDUCE_ADD_CYCLES
    per_ex_bf16 = hop_c + Q["H"] * 2 / lk["bytes_s"] * clk + REDUCE_ADD_CYCLES
    n_ex = 2 * Q["L"] + 1                                   # 2 all-reduces a layer + the argmax gather
    emb_row_bytes = Q["H"] + 2                              # the INT8 row + its BF16 scale
    hops = dict(
        exchanges_per_token=n_ex, all_reduces_per_token=2 * Q["L"], argmax_gathers_per_token=1,
        embedding_row_handoffs_per_token=1,
        all_reduce_bytes_per_direction=ex_bytes, all_reduce_bytes_per_direction_verify_b5=5 * ex_bytes,
        embedding_row_bytes=emb_row_bytes,
        bytes_per_token_per_direction=2 * Q["L"] * ex_bytes + 8 + emb_row_bytes,
        hop_cycles=round(hop_c, 2), transfer_cycles_fp32=round(xfer_c, 2),
        transfer_cycles_fp32_verify_b5=round(5 * xfer_c, 2),
        per_exchange_cycles_fp32=round(per_ex, 2), per_exchange_cycles_o4_bf16=round(per_ex_bf16, 2),
        o4_budget_cycles_per_token=O4["extra_chain_cycles"],
        fp32_cycles_per_token=math.ceil(n_ex * per_ex),
        per_exchange_cycles_verify_b5=round(hop_c + 5 * xfer_c + REDUCE_ADD_CYCLES, 2),
        verify_b5_cycles_per_step=math.ceil(n_ex * (hop_c + 5 * xfer_c + REDUCE_ADD_CYCLES)),
        fp32_plus_embedding_handoff_cycles_per_token=math.ceil(n_ex * per_ex + hop_c + emb_row_bytes / lk["bytes_s"] * clk),
        bandwidth_delay_bytes=round(lk["bytes_s"] * 2 * lk["hop_s"]),
        receiver_buffer_bytes_ar=ex_bytes, receiver_buffer_bytes_verify_b5=5 * ex_bytes,
        average_bytes_s_ar=round((2 * Q["L"] * ex_bytes + 8 + emb_row_bytes) * O4["ar_tokens_s"]),
        link_bytes_s=lk["bytes_s"],
        hop_sensitivity={f"{h * 1e9:g}ns": dict(
            cycles_per_token=math.ceil(n_ex * (h * clk + xfer_c + REDUCE_ADD_CYCLES)),
            ar_tokens_s=round(clk / (O4["calibrated_chain_cycles"] + math.ceil(n_ex * (h * clk + xfer_c + REDUCE_ADD_CYCLES))), 1))
            for h in (lk["hop_s_low"], lk["hop_s"], lk["hop_s_high"])})
    comp = O4["spec_components"]
    lay = {k: v / Q["L"] for k, v in comp.items()}
    ar = dict(
        gate="m = 1, B = 1", target_step_cycles=O4["ar_step_cycles"], tokens_s=O4["ar_tokens_s"],
        per_layer_cycles_budget=round((O4["ar_step_cycles"] - O4["extra_chain_cycles"]
                                       - O4["as_built"]["unit_busy"]["lm_head"]) / Q["L"], 1),
        layer_chain_as_built=O4["as_built"]["layer_chain_cycles"],
        layer_engine_busy_as_built=sum(s[2] for s in O4["as_built"]["layer_stages"]),
        kv_floor_cycles=O4["kv_floor_cycles"], kv_layer_cycles_per_die=round(kv_layer_cycles, 1),
        binding=O4["ar_binding"],
        kv_headroom_over_chain=round(O4["ar_step_cycles"] / O4["kv_floor_cycles"], 3))
    verify = dict(
        gate="m = 5, B = 5", step_cycles=O4["verify_cycles"],
        composition=dict(latency=comp["latency"], control=comp["control"] + O4["extra_chain_cycles"],
                         weights=comp["weights"], attention=comp["attention"],
                         elementwise=5 * comp["elementwise"]),
        per_layer=dict(weights=round(lay["weights"], 1), attention=round(lay["attention"], 1),
                       elementwise_5_slots=round(5 * lay["elementwise"], 1), latency=round(lay["latency"], 1)),
        macs_per_cycle_per_die=5 * lanes, x_operands_per_group_per_cycle=5,
        kv_bytes_read_once=True, new_kv_rows_per_layer_per_die=5 * kv_heads_die * 2)
    draft = dict(step_cycles=O4["draft_cycles"], layers=DRAFTER_LAYERS, fc=DFLASH_FC,
                 fc_die=(DFLASH_FC[0] // TP, DFLASH_FC[1]),
                 fc_die_split_rtl=split_rounds(DFLASH_FC[0] // TP, DFLASH_FC[1], GROUPS_DIE)[0],
                 fc_die_split_golden=G.split_for(DFLASH_FC[0] // TP, DFLASH_FC[1], GROUPS_DIE),
                 tap_hidden_bytes_per_position=DFLASH_TAP_LAYERS * Q["H"] * 4,
                 commit_cycles=O4["commit_cycles"])
    # golden vs RTL K-split at a non-power-of-two group count
    split_check = []
    for name, (n, k) in {**per_layer, **head, "drafter_fc": (DFLASH_FC[0] // TP, DFLASH_FC[1])}.items():
        split_check.append(dict(matrix=name, n=n, k=k, golden=G.split_for(n, k, GROUPS_DIE),
                                rtl=split_rounds(n, k, GROUPS_DIE)[0]))
    attn_golden = G.attn_splits(Q["HD"], GROUPS_DIE)
    scale_rate = max(m["outputs_per_cycle_avg"] for m in mats.values())
    return dict(
        clock_hz=clk, dies=DIES, tp=TP, groups_per_die=GROUPS_DIE, lanes_per_die=lanes,
        lane_multiplier_m=O4["lane_multiplier_m"], copy_lanes_per_die=(O4["lane_multiplier_m"] - 1) * lanes,
        rom=dict(read_bytes_per_cycle_per_die=rom_bpc, read_bits_per_group_per_cycle=W * 8,
                 read_bits_per_group_per_cycle_bf16_now=W * 16,
                 read_bytes_s_per_die=rom_bpc * clk, headroom=O4["rom_read_headroom"],
                 weight_bytes_per_token_per_die=token_w_bytes, weight_bytes_per_layer_per_die=layer_w_bytes,
                 ideal_sweep_cycles_per_token=math.ceil(token_w_bytes / rom_bpc),
                 scale_bytes_per_die=scale_bytes_die,
                 note="one INT8 code a lane a cycle; lane copies share the group's word, so m does not raise it"),
        matrices_per_die=mats, layer_mv_cycles=layer_mv,
        scale_multiply=dict(outputs_per_cycle_sustained_ar=math.ceil(scale_rate),
                            outputs_per_cycle_sustained_verify_m5=math.ceil(5 * scale_rate),
                            burst_outputs_per_cycle_max=max(m["burst_outputs_per_cycle"] for m in mats.values()),
                            multiplies_per_token_per_die=Q["L"] * sum(per_layer[k][0] for k in per_layer)
                            + head["lm_head"][0],
                            assumed_pipe_cycles=FP32_MUL_LAT,
                            chain_cost_cycles_per_token_if_exposed=(4 * Q["L"] + 1) * FP32_MUL_LAT),
        attention=dict(macs_per_layer_per_die=attn_macs_layer_die,
                       ideal_cycles_per_layer=math.ceil(attn_macs_layer_die / lanes),
                       as_built_cycles_per_layer=O4["as_built"]["layer_stages"][1][2],
                       spec_chain_cycles_per_layer=round(lay["attention"], 1),
                       golden_splits_at_6144=dict(scores=attn_golden[0], pv=attn_golden[1]),
                       query_heads_per_die=Q["NH"] // TP, kv_heads_per_die=kv_heads_die),
        kv=dict(heads_per_die=kv_heads_die, bytes_per_layer_per_die=kv_layer_die,
                bytes_per_token_per_die=Q["L"] * kv_layer_die, stacks_per_die=STACKS_DIE,
                sustained_bytes_s_per_die=kv_bw_die, bytes_per_cycle_per_die=round(kv_bpc_die, 1),
                cycles_per_layer=round(kv_layer_cycles, 1), ring_bytes_per_die=round(ring_die),
                write_bytes_per_token_per_die=Q["L"] * 2 * kv_heads_die * Q["HD"] * KV_BYTES),
        stream_unit=dict(width=SU_WIDTH, elementwise_cycles_per_token=comp["elementwise"],
                         elementwise_cycles_per_verify_b5=5 * comp["elementwise"],
                         replicated_on_both_dies=["attention and FFN RMSNorm (sum of squares over H, rsqrt)",
                                                  "residual adds", "final norm", "embedding dequantisation"]),
        ucie=hops, ar=ar, verify=verify, draft=draft,
        dflash=dict(block=O4["dflash_block"], tokens_per_step=O4["tokens_per_step"], step_cycles=O4["step_cycles"],
                    tokens_s=O4["dflash_tokens_s"], acceptance_basis="BF16 GPU measurement; 8-bit not measured"),
        split_rule_check=split_check,
        split_rule_divergent=[r["matrix"] for r in split_check if r["golden"] != r["rtl"]])


# -- 1b. the die split: every layer split (TP-2) or a contiguous layer cut -----------------------------------------
# ROM cells (tools/qwen3_8bit_design.capacity, CimCellAccounting): an INT8 weight is 2 select cells, a BF16 scale or
# norm weight 4; the O4 capacity's 381.029 mm2 for the 36 layers' 13,898,371,072 cells gives the area a cell.
CELL_MM2 = 381.029 / 13898371072
ROM_READ_B_S_MM2, ROM_READ_EFF = 705555555555.5555, 0.75       # O4 density: 8-bit read density, efficiency
DIE_ROM_BUDGET_MM2 = 224.65 + 28.76 + 28.21                     # O4 ledger a die: target + drafter ROM + slack
DRAFTER_CELLS = 2098148352                                      # O4 capacity: drafter (INT8 + scales + norms)
# The layer cut at batch 1 runs one die at a time, so its step is one 6,144-group engine on 4 stacks: the O4 tool's
# perf() at dies=1, groups=6144, stacks_per_die=4, m=5 (claude/qwen-o4 @ 58d70929, tools/qwen3_8bit_design.perf;
# computed for this audit, carried here), plus the handoffs below.
LAYER_CUT_MODEL = dict(ar_step_cycles=184321, ar_binding="hbm_stream", calibrated_chain_cycles=160881,
                       dflash_b5_step_cycles=252001, dflash_b5_draft_cycles=37251, dflash_b5_verify_cycles=214740)
DFLASH_TAPS = (1, 9, 17, 25, 33)                                # the drafter's fc reads these target layers' outputs


def _layer_cells():
    H, NH, KV, HD, FF = (Q[k] for k in ("H", "NH", "KV", "HD", "FF"))
    elems = (NH + 2 * KV) * HD * H + H * NH * HD + 2 * FF * H + H * FF
    rows = (NH + 2 * KV) * HD + H + 2 * FF + H                  # one BF16 scale per output row
    norms = 2 * H + 2 * HD                                      # input/post norms (folded but stored), q/k norms
    return 2 * elems + 4 * rows + 4 * norms


def die_split():
    clk = O4["clock_hz"]
    lk = link()
    hop = lk["hop_s"] * clk
    xfer = lambda b: b / lk["bytes_s"] * clk                   # noqa: E731
    lay = _layer_cells()
    vocab_cells = 2 * Q["V"] * Q["H"] + 4 * Q["V"]              # embedding or lm_head: INT8 rows + row scales
    need = GROUPS_DIE * W * clk                                 # ROM bytes a second a die at one INT8 a lane a cycle

    def headroom(swept_cells):
        return swept_cells * CELL_MM2 * ROM_READ_B_S_MM2 * ROM_READ_EFF / need

    # TP-2: half of everything on each die
    tp_swept = (36 * lay + 4 * Q["H"] + vocab_cells) / 2
    tp_total = (36 * lay + 4 * Q["H"] + 2 * vocab_cells + DRAFTER_CELLS) / 2
    tp = dict(die0="half of every layer (16 query heads, 4 KV heads, half the FFN), half the embedding and lm_head "
                   "vocabulary, half the drafter",
              die1="the other half",
              rom_mm2_per_die=round(tp_total * CELL_MM2, 2), rom_read_headroom=round(headroom(tp_swept), 3),
              ar_tokens_s=O4["ar_tokens_s"], dflash_tokens_s=O4["dflash_tokens_s"],
              handoff="73 exchanges a token (section 4 figures)")
    # contiguous cut: die A = embedding + layers [0, P); die B = layers [P, 36) + final norm + lm_head + drafter
    rows = []
    for P in range(16, 25):
        a_swept = P * lay
        b_swept = (36 - P) * lay + 4 * Q["H"] + vocab_cells
        a_tot = a_swept + vocab_cells
        b_tot = b_swept + DRAFTER_CELLS
        rows.append(dict(P=P, die_a_layers=f"0-{P - 1}", die_b_layers=f"{P}-35",
                         die_a_rom_mm2=round(a_tot * CELL_MM2, 2), die_b_rom_mm2=round(b_tot * CELL_MM2, 2),
                         both_fit=max(a_tot, b_tot) * CELL_MM2 <= DIE_ROM_BUDGET_MM2,
                         die_a_rom_read_headroom=round(headroom(a_swept), 3),
                         die_b_rom_read_headroom=round(headroom(b_swept), 3)))
    # the cut: both dies fit; the worse ROM-read headroom highest; then the smaller area imbalance
    fit = [r for r in rows if r["both_fit"]]
    best = max(fit, key=lambda r: (min(r["die_a_rom_read_headroom"], r["die_b_rom_read_headroom"]),
                                   -abs(r["die_a_rom_mm2"] - r["die_b_rom_mm2"])))
    P = best["P"]
    taps_on_a = [t for t in DFLASH_TAPS if t < P]
    fwd_ar = Q["H"] * 4                                         # FP32 residual: consumed by the residual add and rstd
    back_ar = 4                                                 # the token id, for die A's embedding lookup
    fwd_v = 5 * Q["H"] * 4 + len(taps_on_a) * 5 * Q["H"] * 2    # 5 slots' residuals + taps (BF16: only a matvec reads)
    back_v = 5 * 4 + 4                                          # 5 draft tokens + the accepted count
    ar_x = math.ceil(hop + xfer(fwd_ar)) + math.ceil(hop + xfer(back_ar))
    v_x = math.ceil(hop + xfer(fwd_v)) + math.ceil(hop + xfer(back_v))
    lc = LAYER_CUT_MODEL
    ar_step = lc["ar_step_cycles"] + ar_x
    df_step = lc["dflash_b5_step_cycles"] + v_x
    cut = dict(P=P, die_a=f"embedding + layers 0-{P - 1}", die_b=f"layers {P}-35 + final norm + lm_head + drafter",
               why_drafter_on_b="it shares the lm_head (die B) and its draft feeds die B's verify tail; its fc "
                                f"taps {taps_on_a} come from die A with the verify's handoff",
               row=best,
               handoff_ar=dict(a_to_b_bytes=fwd_ar, b_to_a_bytes=back_ar, cycles_per_token=ar_x,
                               position="between layer P-1 and P (A->B), and after the argmax (B->A): both "
                                        "serial on the token's chain"),
               handoff_dflash_b5=dict(a_to_b_bytes=fwd_v, b_to_a_bytes=back_v, cycles_per_step=v_x,
                                      taps_on_die_a=taps_on_a),
               ar_step_cycles=ar_step, ar_tokens_s=round(clk / ar_step, 1),
               ar_binding=lc["ar_binding"],
               dflash_step_cycles=df_step, dflash_tokens_s=round(O4["tokens_per_step"] * clk / df_step, 1),
               vs_o4_ar=round((clk / ar_step) / O4["ar_tokens_s"], 3),
               vs_o4_dflash=round((O4["tokens_per_step"] * clk / df_step) / O4["dflash_tokens_s"], 3),
               model=LAYER_CUT_MODEL,
               why_slower="at batch 1 token t+1 needs token t, so one die works at a time: half the lanes and "
                          "half the stacks serve every token; with each die's KV on its own 4 stacks the KV "
                          "floor doubles (184,321 cycles) and binds")
    return dict(tp2=tp, layer_cut=cut, layer_cut_sweep=rows,
                recommendation="TP-2 (every layer split) is the only split that reaches the O4 rates at batch 1; "
                               f"if a contiguous cut is kept, cut at P = {P}")


# -- 2. numerics ----------------------------------------------------------------------------------------------------
def _bits(a):
    a = np.asarray(a, dtype=np.float32)
    a = np.where(a == 0, np.float32(0), a).astype(np.float32)        # canonical +0 (the golden's z)
    return a.view(np.uint32)


def _ulps(a, b):
    ia = _bits(a).astype(np.int64)
    ib = _bits(b).astype(np.int64)
    ia = np.where(ia & 0x80000000, 0x80000000 - ia, ia)
    ib = np.where(ib & 0x80000000, 0x80000000 - ib, ib)
    return np.abs(ia - ib)


def _harness():
    try:
        import torch  # noqa: F401
        import qwen3_deployment_quality as QH
        return QH
    except Exception:  # pragma: no cover
        return None


def quantize_rows(w, QH=None):
    """Signed symmetric INT8, one BF16 scale per output row.  With the harness importable: its own quantiser
    (_rtn_mse at 8 bits: codes -128..127, scale bf16(amax x r / 127), clip r by per-row MSE search) with one group
    per row; else plain absmax."""
    if QH is not None:
        import torch
        wt = torch.from_numpy(np.ascontiguousarray(w, dtype=np.float32))[:, None, :]
        q, s, _ = QH._rtn_mse(wt, 8)
        return q[:, 0, :].numpy().astype(np.int8), s[:, 0, 0].to(torch.float32).numpy()
    amax = np.maximum(np.abs(w).max(1), 1e-30)
    s = G.to_bf16((amax / 127).astype(np.float32))
    q = np.clip(np.rint(w / s[:, None]), -128, 127).astype(np.int8)
    return q, s


def harness_per_mac(QH, x, codes, s, S):
    """The harness's quantised matvec (tools/qwen3_deployment_quality._chunk_tree_dot_ref, the CPU reference of its
    Triton kernel): w = code x scale in FP32, then the golden's chunk + pairwise-tree order."""
    import torch
    K = codes.shape[1]
    y = QH._chunk_tree_dot_ref(torch.from_numpy(G.to_bf16(x))[None], torch.from_numpy(codes),
                               S, torch.from_numpy(s.astype(np.float32))[:, None], K)
    return y[0].numpy()


def contract_mv(x, codes, s, S):
    """THE CONTRACT: T = golden matvec of the INT8 codes (exact in BF16) and bf16(x), K-split S; y = fl32(T x s)."""
    T = G.matvec(codes.astype(np.float32), x, S)
    return G.mul(T, s), T


def _load_real(rows, seed):
    """Real Qwen3-8B rows (layer 0 and the lm_head) from the HF snapshot, norm-folded as the vector core folds them
    (W' = bf16(W diag(w))), each die's TP-2 slice shape.  None if the snapshot is absent."""
    try:
        from safetensors import safe_open
        snaps = sorted(Path.home().glob(".cache/huggingface/hub/models--Qwen--Qwen3-8B/snapshots/*/config.json"))
        snap = snaps[0].parent
        idx = json.loads((snap / "model.safetensors.index.json").read_text())["weight_map"]
    except Exception:
        return None
    import torch

    def get(name):
        with safe_open(str(snap / idx[name]), framework="pt") as h:
            return h.get_tensor(name).to(torch.float32).numpy()
    rng = np.random.default_rng(seed)
    p = "model.layers.0."
    ln1, ln2 = get(p + "input_layernorm.weight"), get(p + "post_attention_layernorm.weight")
    emb = get("model.embed_tokens.weight")
    xs = {4096: emb[rng.integers(0, emb.shape[0])] * 8.0 + rng.standard_normal(4096).astype(np.float32) * 0.5}
    out = {}
    for key, name, fold, kslice in (("qkv(q)", "self_attn.q_proj.weight", ln1, None),
                                     ("o", "self_attn.o_proj.weight", None, (0, 2048)),
                                     ("gate_up(gate)", "mlp.gate_proj.weight", ln2, None),
                                     ("down", "mlp.down_proj.weight", None, (0, 6144))):
        w = get(p + name)
        r = rng.choice(w.shape[0], rows, replace=False)
        w = w[r]
        if fold is not None:
            w = G.fold_cols(w, fold)
        if kslice:
            w = w[:, kslice[0]:kslice[1]]
        out[key] = w
    lm = get("lm_head.weight")
    out["lm_head"] = lm[rng.choice(lm.shape[0], rows, replace=False)]
    xs[2048] = rng.standard_normal(2048).astype(np.float32) * 0.05
    xs[6144] = (rng.standard_normal(6144).astype(np.float32) * 0.1) * np.abs(rng.standard_normal(6144)).astype(np.float32)
    emb_rows = emb[rng.choice(emb.shape[0], 64, replace=False)]
    return out, xs, emb_rows


def _synthetic(rows, seed):
    rng = np.random.default_rng(seed)
    mats = {}
    for key, k in (("qkv(q)", 4096), ("o", 2048), ("gate_up(gate)", 4096), ("down", 6144), ("lm_head", 4096)):
        w = rng.standard_normal((rows, k)).astype(np.float32) * 0.02
        w[:, rng.choice(k, 8, replace=False)] *= 20.0                      # outlier columns, as in real weights
        mats[key] = G.to_bf16(w)
    xs = {k: (rng.standard_normal(k) * np.abs(rng.standard_normal(k))).astype(np.float32) for k in (2048, 4096, 6144)}
    return mats, xs, G.to_bf16(rng.standard_normal((64, 4096)).astype(np.float32) * 0.02)


def numerics(rows=192, seed=0, real=True):
    QH = _harness()
    src = _load_real(rows, seed) if real else None
    source = "Qwen3-8B HF snapshot (layer 0, lm_head), norm-folded, TP-2 die shapes" if src else "synthetic"
    mats, xs, emb_rows = src if src else _synthetic(rows, seed)
    full_n = {"qkv(q)": 3072, "o": 4096, "gate_up(gate)": 12288, "down": 4096, "lm_head": 75968}
    res = {}
    all_exact = True
    for key, w in mats.items():
        K = w.shape[1]
        x = xs[K]
        codes, s = quantize_rows(w, QH)
        S = G.split_for(full_n[key], K, GROUPS_DIE)
        y, T = contract_mv(x, codes, s, S)
        # exactness of the pieces the contract relies on
        xb = G.to_bf16(x).astype(np.float64)
        prod64 = codes.astype(np.float64) * xb[None, :]
        prod_exact = bool(np.all(prod64.astype(np.float32).astype(np.float64) == prod64))
        code_bf16_exact = bool(np.all(G.to_bf16(codes.astype(np.float32)) == codes.astype(np.float32)))
        scale_bf16 = bool(np.all(G.to_bf16(s) == s))
        # the harness order (scale in every product) and the golden with pre-scaled weights
        wq = G.mul(codes.astype(np.float32), s[:, None])                  # code x scale: exact (<= 15 bits)
        permac_golden = G.matvec(wq, x, S)
        r = dict(rows=int(w.shape[0]), k=int(K), split=int(S), products_exact_fp32=prod_exact,
                 codes_exact_in_bf16=code_bf16_exact, scales_are_bf16=scale_bf16,
                 code_range=[int(codes.min()), int(codes.max())])
        d_gold = _bits(permac_golden) != _bits(y)
        r["per_mac_golden_vs_contract_rows_differing"] = int(d_gold.sum())
        r["per_mac_golden_vs_contract_max_ulp"] = int(_ulps(permac_golden, y).max())
        if QH is not None:
            hp = harness_per_mac(QH, x, codes, s, S)
            r["harness_equals_golden_per_mac"] = bool(np.array_equal(_bits(hp), _bits(permac_golden)))
            r["harness_vs_contract_rows_differing"] = int((_bits(hp) != _bits(y)).sum())
            r["harness_vs_contract_max_ulp"] = int(_ulps(hp, y).max())
            r["harness_vs_contract_max_rel"] = float(np.max(np.abs(hp.astype(np.float64) - y) /
                                                            np.maximum(np.abs(y.astype(np.float64)), 1e-30)))
        all_exact &= prod_exact and code_bf16_exact and scale_bf16
        res[key] = r
    # TP fold: scale each die's partial then fold, or fold then scale once
    w = mats["down"]
    K = w.shape[1]
    codes, s = quantize_rows(w, QH)
    x = xs[K]
    h = K // 2
    S = G.split_for(4096, h, GROUPS_DIE)
    T0 = G.matvec(codes[:, :h].astype(np.float32), x[:h], S)
    T1 = G.matvec(codes[:, h:].astype(np.float32), x[h:], S)
    a = G.add(G.mul(T0, s), G.mul(T1, s))
    b = G.mul(G.add(T0, T1), s)
    fold = dict(rows=int(w.shape[0]), rows_differing=int((_bits(a) != _bits(b)).sum()),
                max_ulp=int(_ulps(a, b).max()))
    # embedding: x = code x scale is one exact product
    ec, es = quantize_rows(emb_rows, QH)
    e64 = ec.astype(np.float64) * es.astype(np.float64)[:, None]
    emb_exact = bool(np.all(e64.astype(np.float32).astype(np.float64) == e64))
    tot = sum(r.get("harness_vs_contract_rows_differing", r["per_mac_golden_vs_contract_rows_differing"])
              for r in res.values())
    n = sum(r["rows"] for r in res.values())
    return dict(
        source=source, quantiser="tools/qwen3_deployment_quality._rtn_mse at 8 bits, one group per output row"
        if QH is not None else "absmax INT8 per row (harness not importable)",
        harness_importable=QH is not None, groups=GROUPS_DIE, matrices=res,
        pieces_exact=all_exact, embedding_dequant_exact=emb_exact,
        tp_fold_scale_order=fold,
        harness_order_rows_differing=tot, rows_checked=n,
        bit_exact_with_harness_order=tot == 0,
        verdict=("NOT bit-exact: the harness's quantised kernel scales every product (w = code x scale) and "
                 "accumulates the scaled products, the contract accumulates the unscaled INT8 x BF16 products and "
                 "scales the FP32 sum once; the rounding of every accumulation step differs")
        if tot else "bit-exact")


# -- 3. gaps --------------------------------------------------------------------------------------------------------
GAPS = [
    dict(id="G1", block="ROM weight word and image",
         current="wrom_q is G x W x 16 bits: one BF16 a lane (ot_hdc_core.sv, ot_hdc_matvec.sv); "
                 "hdc_program.place_matrix writes BF16 top halves; 16 bits a lane also in hbm_weight_image, "
                 "pack_lanes(w,16) and hdc_timing.price_hbm",
         required="one signed INT8 code a lane a cycle: 128 bits a group a cycle, 98,304 B a cycle a die; image "
                  "writer packs INT8 codes of the norm-folded matrices",
         size="M", owner="Codex"),
    dict(id="G2", block="Weight decode to the MAC operand",
         current="{wrom[16l+:16], 16'h0}: BF16 widened to binary32 (ot_hdc_matvec.sv)",
         required="INT8 code to an exact BF16/FP32 operand (every code -128..127 is exact in BF16), no rounding",
         size="S", owner="Codex"),
    dict(id="G3", block="MAC lane and accumulation",
         current="ot_hdc_bmul exact BF16 x BF16 -> FP32, ot_hdc_fadd RNE circulating, K-split chunks + pairwise "
                 "ot_hdc_qadd tree",
         required="unchanged: INT8 x BF16 products are exact in FP32 (<= 15 significant bits), accumulation order "
                  "is the golden's; a narrower INT8 x BF16 multiplier is a power lever, not a requirement",
         size="none", owner="Codex"),
    dict(id="G4", block="Per-output-channel scale multiply",
         current="none: the matvec result (lvl[LG] -> o_data) is the FP32 sum",
         required="one FP32 x BF16 RNE multiply per output row after the split tree and before argmax / "
                  "writeback / the TP exchange; >= 47 outputs a cycle a die sustained (233 at m = 5), bursts up to "
                  "(G/S) x W = 1,536; scale table 1.90 MB a die incl. lm_head, embedding and drafter",
         size="M", owner="Codex"),
    dict(id="G5", block="Lane copies (m = 5) and verify slots",
         current="ot_hdc_lane_copy.sv is an area probe, instantiated nowhere; one x operand a group; no Qwen "
                 "verify slots",
         required="4 MAC-only copies a lane (393,216 copy lanes a die) sharing the group's weight word; 5 x "
                  "operands a group a cycle; 5 accumulators and results a lane; the KV word shared by 5 slots' "
                  "scores and P.V with the block's causal mask",
         size="L", owner="Codex"),
    dict(id="G6", block="Matrix engine size and split rule at 6,144 groups",
         current="reduced vehicle G = 4 (8 in one campaign); spec 8,192 (a power of two); golden split_for "
                 "packs ceil(tiles x S / G), the RTL floor(G / S) tiles a round",
         required="6,144 groups a die (not a power of two): the golden and the RTL must choose the same K-split "
                  "(they differ for the drafter fc slice: golden S = 4096, RTL rule S = 1024)",
         size="S", owner="Codex"),
    dict(id="G7", block="Stream unit",
         current="ot_hdc_vstream SW lanes (reduced gates SW = 16), R-ARITH reductions, embedding row read as BF16",
         required="SW = 1,024 a die; norms and residuals replicated on both dies; 5 slots' elementwise work in "
                  "the verify (48,960 cycles a step at SW = 1,024); embedding row as INT8 + scale (exact product)",
         size="M", owner="Codex"),
    dict(id="G8", block="KV path per die",
         current="ot_hdc_qwen_kv_system: one 32-B HBM request port, one outstanding request (phys arbiter); HBM "
                 "model of 2-4 pseudo-channels of one stack; FP8 E4M3 KV",
         required="4 HBM3E stacks a die at 3.6 TB/s sustained (3,277 B a cycle), its 4 KV heads; a ring of one "
                  "layer of the die's KV (8.4 MB at 8K) + refresh cover (9.65 MB); 5 new rows a head a layer "
                  "in the verify",
         size="L", owner="Codex"),
    dict(id="G9", block="UCIe TP-2 collectives",
         current="rtl/rom ot_rom_oneshot_allreduce (N-parametric, rank-order FP32 fold, credits), "
                 "ot_rom_tp_seq, ot_rom_ucie_link; run only at D = 4 with the scalar ot_hdc_core (SU_VEC = 0)",
         required="TP-2 with the vector core: 2 all-reduces a layer of H FP32 partials (16 KiB a direction; "
                  "80 KiB at B = 5), argmax gather, embedding-row handoff; <= ~19 cycles exposed an exchange "
                  "(1,251 cycles a token in the O4 rate); no credit round trip on the chain",
         size="M", owner="Codex"),
    dict(id="G10", block="Embedding and lm_head",
         current="embedding BF16 in wrom read by the stream unit; lm_head BF16 rows, matvec argmax over the "
                 "unscaled result; argmax gather in ot_rom_tp_seq",
         required="INT8 rows + BF16 row scales; vocabulary split 75,968 rows a die; scale before the argmax "
                  "compare; per-slot argmax for 5 verify slots and the drafter's 4 draft slots",
         size="M", owner="Codex"),
    dict(id="G11", block="DFlash drafter and accept",
         current="no Qwen drafter, verify or accept RTL (ot_hdc_accept.sv is instantiated only by the V4.1 cores)",
         required="drafter (fc 4096 x 20480 + 5 layers, INT8, TP-2) on the same engine and copies within 26,677 "
                  "cycles a step; target hidden-state taps of 5 layers; accept/commit within 10 cycles",
         size="L", owner="Codex"),
    dict(id="G12", block="ISA and program generator",
         current="ME fields carry no weight format or scale base; place_matrix BF16; --tp emits per-die images but "
                 "NORM_FOLD is off for tp > 1; no slot count or drafter program",
         required="8-bit images and a scale table; TP-2 program with norm fold; verify-slot and drafter programs "
                  "from the same source",
         size="M", owner="Codex"),
    dict(id="G13", block="Golden model (hdc_golden.py)",
         current="BF16 weights only, no quantiser; decode_token_tp unfolded norms and BF16 KV",
         required="INT8 codes + per-row BF16 scales with the post-accumulation contract; TP-2 with NORM_FOLD and "
                  "FP8 KV; the scale's order around the fold pinned; B = 5 verify and drafter golden",
         size="M", owner="Claude"),
    dict(id="G14", block="Quality harness 8-bit mode",
         current="w8 mode (g_contract_w8, e_full_w8): codes x BF16 summed in the golden K-split order, one scale "
                 "multiply after the sum; 0 of the 960 section 3.2 outputs differ from the contract (the group "
                 "formats still scale every product); the 8-bit quality verdict is not yet run",
         required="a per-channel INT8 mode that scales after the chunk-tree sum, bit-exact with G13; the 8-bit "
                  "quality verdict (<= 2% perplexity, <= 1 MMLU point) and DFlash acceptance at 8 bits",
         size="S", owner="Claude"),
    dict(id="G15", block="Timing and performance models",
         current="O4 priced per die (qwen3_8bit_design): calibrated replay of one die's TP-2 slice at 6,144 "
                 "groups, 73 FP32-partial exchanges (1,407 cycles) + embedding handoff, 5-cycle scale stage, golden "
                 "K-splits; the verify at m = 5 on the spec chain (a calibrated-core estimate beside it)",
         required="per-die TP-2 replay at 6,144 groups with the scale stage and FP32 partials; verify at m = 5 on "
                  "the calibrated core",
         size="M", owner="Claude"),
    dict(id="G16", block="Reduced vehicle",
         current="every RTL gate uses the BF16 random reduced checkpoint (hidden 128, 4 layers)",
         required="an INT8-quantised reduced vehicle (codes + non-trivial row scales) the golden and the gates "
                  "share",
         size="S", owner="Claude"),
    dict(id="G17", block="Reduced two-die gates",
         current="package TP bench at D = 4 with scalar cores; no two-die vector-core gate; no DFlash gate",
         required="two gates on one program: autoregressive (m = 1) and DFlash verify (m = 5, B = 5), TP-2, "
                  "bit-exact tokens and KV against the golden",
         size="M", owner="Codex"),
]


def check_o4_file():
    """Cross-check the carried O4 figures against the record when it is on disk."""
    if not O4_FILE.exists():
        return dict(present=False)
    d = json.loads(O4_FILE.read_text())
    c = d.get("configurations", {}).get("O4_two_reticles_one_package")
    if c is None:
        return dict(present=True, has_o4=False)
    p, led = c["performance"], c["ledger"]
    b = p["dflash"]["best"]
    pairs = dict(ar_tokens_s=p["ar_tokens_s"], ar_step_cycles=p["ar_step_cycles"],
                 kv_floor_cycles=p["kv_floor_cycles"], plain_cycles=p["dflash"]["plain_cycles"],
                 step_cycles=b["step_cycles"], verify_cycles=b["verify_cycles"], draft_cycles=b["draft_cycles"],
                 dflash_tokens_s=b["tokens_s"], groups_per_die=led["groups_per_die"],
                 lane_multiplier_m=led["lane_multiplier_m"])
    return dict(present=True, has_o4=True, mismatches={k: [v, O4[k]] for k, v in pairs.items() if v != O4[k]})


def build(rows=192, real=True):
    return dict(
        schema=SCHEMA, tool="tools/qwen3_o4_rtl_gaps.py", doc="docs/ARCH_QWEN3_O4_RTL_SPEC.md",
        status="ADVISORY: performance requirements and gap audit (input to the RTL contract Codex owns)",
        design="O4: two reticles, one package, TP-2 over UCIe, INT8 weight-only with per-output-channel BF16 "
               "scales, 8 HBM3E stacks (4 a die), 6,144 groups a die, m = 5",
        o4=O4, o4_file_check=check_o4_file(),
        requirements=requirements(),
        die_split=die_split(),
        numerics=numerics(rows=rows, real=real),
        numeric_contract=[
            "C0 quantiser: offline, a model-side choice pinned in the manifest (the RTL consumes codes and scales "
            "as data); codes are clamped to [-128, 127] at quantisation, so the datapath has no saturation; the "
            "reduced vehicle uses the harness's RTN-MSE rule (_rtn_mse at 8 bits: s = bf16(amax x r / 127), "
            "r in linspace(0.5, 1, 21) by row MSE, q = clamp(round-half-even(w / s)))",
            "C1 weights: signed INT8 codes q in [-128, 127], symmetric (no zero point), of the norm-folded BF16 "
            "matrix W' = bf16(W diag(w)) for q/k/v and gate/up, W itself for o, down, lm_head; one BF16 scale s_n "
            "per output row n (per vocabulary row for the embedding and the lm_head)",
            "C2 products: bf16(x_k) x q_nk formed exactly in FP32 (<= 15 significant bits), the golden's K-split "
            "order: S contiguous chunks each summed sequentially from +0 in FP32 RNE, chunk sums a pairwise tree",
            "C3 scale: y_n = fl32(T_n x s_n), one binary32 RNE multiply of the FP32 sum by the BF16 scale (gradual "
            "underflow, canonical +0, the qualified ot_fp32_mul_rne_pipe arithmetic); y_n stays FP32 -- it is NOT "
            "rounded to BF16; BF16 rounding happens only where the golden already rounds (the next matvec's input, "
            "q and the probabilities before attention) and FP8 at the KV write",
            "C4 norm fold: q, k, v, gate, up = fl32(y_n x r) with r = rstd(x), i.e. scale first, then 1/rms",
            "C5 embedding: x_h = q_th x s_t, exact in FP32 (no rounding)",
            "C6 lm_head: logits_n = fl32(T_n x s_n); the argmax compares scaled logits, ties to the lower index",
            "C7 TP-2 row-split (o, down): each die scales its partial (C3) and the partials are folded in rank "
            "order, fl32(y0 + y1) -- or fold first and scale once; the two differ (numerics.tp_fold_scale_order) "
            "and the golden must pin one"],
        gaps=GAPS,
        size_legend=dict(none="no RTL change", S="a parameter or a local edit (<~100 lines)",
                         M="a new or reworked block within one module family",
                         L="a new subsystem or a cross-module datapath change"),
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--rows", type=int, default=192)
    ap.add_argument("--synthetic", action="store_true", help="skip the HF snapshot")
    a = ap.parse_args()
    out = build(rows=a.rows, real=not a.synthetic)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    n = out["numerics"]
    print(f"numerics: {n['source']}: {n['harness_order_rows_differing']}/{n['rows_checked']} rows differ "
          f"(harness order vs contract); pieces exact {n['pieces_exact']}; fold orders differ in "
          f"{n['tp_fold_scale_order']['rows_differing']} rows")
    r = out["requirements"]
    print(f"ROM {r['rom']['read_bytes_per_cycle_per_die']} B/cycle/die; KV {r['kv']['bytes_per_cycle_per_die']} "
          f"B/cycle/die; UCIe {r['ucie']['fp32_cycles_per_token']} cycles/token (O4 {O4['extra_chain_cycles']}); "
          f"layer cut P={out['die_split']['layer_cut']['P']} {out['die_split']['layer_cut']['ar_tokens_s']} tok/s; split divergent "
          f"{r['split_rule_divergent']}")
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
