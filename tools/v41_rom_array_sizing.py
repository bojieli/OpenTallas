#!/usr/bin/env python3
"""PARTIAL (W8, halted 2026-09-29): top-down MAC sizing of the V4.1 ROM layer die's bank-local compute array.

Analytical only, no RTL.  Inputs are the busiest die's integer bank map (W1), the checkpoint config and the
lanes design point.  The model: every weight word the token needs must be read from a ROM macro (one
274-bit word per macro per cycle), so the per-token ROM-MAC cycle floor on a die is
    words_needed / macros_read_in_parallel.
Contiguous layout (each expert matrix slice in its own 8 macros, as bank-mapped by W1) reads one slice
serially from 8 macros; striped layout (every output row owned by one cluster, rows of every expert and
dense matrix interleaved over all macros) reads from all macros at once.

    python3 tools/v41_rom_array_sizing.py --output results/floorplan/v41_rom_array_sizing.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BANKMAP = "results/floorplan/v41_die_bankmap_busiest_expanded_woa.json"
LANES = "results/arch/v41_lanes.json"
ASSEMBLY = "results/arch/v41_die_assembly.json"
PACK = "results/floorplan/v41_pack_expanded_woa.json"
CLOCK_HZ = 1.087e9
# DeepSeek-V4.1-Flash config.json (snapshot dba1be0a...): read from the checkpoint when present
CFG = dict(hidden=5120, moe_inter=2304, n_routed=384, topk=6, q_lora=1280, heads=64, head_dim=512,
           o_groups=8, o_lora=1024, layers=40, mtp_layers=3, index_heads=32, index_head_dim=128)
TP = 4
FP4_LANES_PER_WORD = 2      # two 136-bit paired-FP4 32-blocks per 274-bit word
FP8_LANES_PER_WORD = 1      # one 264-bit {UE8M0, 32 x E4M3} block per word
BF16_PER_WORD = 16          # bf16_expanded_256bit
MAC_PER_BLOCK = 32


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    bm = json.loads((ROOT / BANKMAP).read_text())
    lanes = json.loads((ROOT / LANES).read_text())
    asm = json.loads((ROOT / ASSEMBLY).read_text())

    experts = Counter()
    dense = {}
    for e in bm["entries"]:
        m = re.match(r"layers\.(\d+)\.ffn\.experts\.(\d+)\.w1", e["tensor"])
        if m:
            experts[int(m.group(1))] += 1
        elif e["group"] == "ROM_MAC.dense_QE" or e["group"] == "ROM_MAC.ME":
            n = int(e["last"].split("#")[1]) - int(e["first"].split("#")[1]) + 1
            dense[e["tensor"].split(".", 2)[-1]] = dict(macros=n, rank_shape=e.get("rank_shape"),
                                                       representation=e.get("representation"))
    macros_total = bm["macro_totals"]["ot_rom_8192x274_m8"]
    h, f = CFG["hidden"], CFG["moe_inter"]
    # per expert per die (TP-4 output-row quarter of w1/w3, output-row quarter of w2 -- the mandatory w2 split)
    w13_rows, w2_rows = f // TP, h // TP
    blk_w13 = w13_rows * (h // 32)
    blk_w2 = w2_rows * (f // 32)
    words_expert = (2 * blk_w13 + blk_w2) // FP4_LANES_PER_WORD
    exp_active = {L: CFG["topk"] * n / CFG["n_routed"] for L, n in experts.items()}
    exp_worst = {L: min(CFG["topk"], n) for L, n in experts.items()}
    # dense FP8 (block-dots = words), shared expert is FP8 on this die (16 macros per matrix)
    dense_words = 0
    for k, v in dense.items():
        if v["representation"] and v["representation"].startswith("fp8") and v["rank_shape"]:
            r, kk = v["rank_shape"]
            dense_words += r * (kk // 32)
    shared_words = 2 * blk_w13 + blk_w2           # FP8: one block per word
    dense_words += shared_words
    woa = dense.get("attn.wo_a.weight", {})
    woa_words = (woa["rank_shape"][0] * woa["rank_shape"][1]) // BF16_PER_WORD if woa else 0

    exp_words_exp = sum(exp_active.values()) * words_expert
    exp_words_worst = sum(exp_worst.values()) * words_expert
    tot_exp = exp_words_exp + dense_words + woa_words
    tot_worst = exp_words_worst + dense_words + woa_words
    per_macro = lambda w: w / macros_total

    dp = lanes["design_point"]["1048576"]["breakdown_us"]
    stages = 28
    sweep_us_per_stage = dp["weight_sweep"] / stages
    budget_cycles = sweep_us_per_stage * 1e-6 * CLOCK_HZ

    rec = {
        "schema": "opentallas.v41-rom-array-sizing.v0",
        "status": "PARTIAL: analytical derivation only; W8 halted by root before RTL/verification/physical",
        "tool": "tools/v41_rom_array_sizing.py",
        "source_sha256": {p: sha(p) for p in (BANKMAP, LANES, ASSEMBLY, "tools/v41_rom_array_sizing.py")},
        "model_config": CFG, "tp": TP, "clock_hz": CLOCK_HZ,
        "busiest_die": {"stage": bm["stage"], "rank": bm["rank"], "rom_macros": macros_total,
                        "experts_per_layer_on_die": dict(experts), "dense_and_me": dense},
        "per_expert_per_die": {"w1_w3_rows": w13_rows, "w1_w3_blocks_per_row": h // 32, "w2_rows": w2_rows,
                               "w2_blocks_per_row": f // 32, "block_dots": 2 * blk_w13 + blk_w2,
                               "macs": (2 * blk_w13 + blk_w2) * MAC_PER_BLOCK, "rom_words_fp4_pair": words_expert,
                               "rows_per_macro_contiguous": blk_w13 // FP4_LANES_PER_WORD // 8},
        "active_experts_on_die": {"expected_uniform_routing": exp_active, "worst_case": exp_worst},
        "rom_words_per_token": {"experts_expected": exp_words_exp, "experts_worst": exp_words_worst,
                                "dense_fp8_incl_shared": dense_words, "wo_a_bf16": woa_words,
                                "total_expected": tot_exp, "total_worst": tot_worst},
        "read_floor_cycles_per_token": {
            "contiguous_one_expert_matrix_sweep": blk_w13 // FP4_LANES_PER_WORD // 8,
            "contiguous_moe_chain_w13_then_w2": 2 * (blk_w13 // FP4_LANES_PER_WORD // 8),
            "contiguous_wq_b": (lambda v: v["rank_shape"][0] * (v["rank_shape"][1] // 32) / v["macros"])(
                dense["attn.wq_b.weight"]) if "attn.wq_b.weight" in dense else None,
            "contiguous_wo_a_64_macros": woa_words / woa["macros"] if woa else None,
            "striped_all_macros_expected": per_macro(tot_exp),
            "striped_all_macros_worst": per_macro(tot_worst),
        },
        "budget": {"weight_sweep_us_per_token_design_point_1M": dp["weight_sweep"], "stages": stages,
                   "weight_sweep_cycles_per_stage": budget_cycles,
                   "source": LANES + " design_point.1048576.breakdown_us.weight_sweep"},
        "element_per_macro": {"fp4_block_dot_lanes": 2, "fp4_macs": 2 * MAC_PER_BLOCK,
                              "fp8_block_dot_lanes": 1, "bf16_macs": BF16_PER_WORD},
        "die_totals_sharing_1": {"block_dot_macs": macros_total * 2 * MAC_PER_BLOCK,
                                 "bf16_macs": macros_total * BF16_PER_WORD},
        "ledger": {"weight_macs": asm["design_point"]["widths"]["weight_macs"],
                   "bf16_macs": asm["design_point"]["widths"]["bf16_macs"],
                   "lane_mult_mtp": asm["design_point"]["widths"]["lane_mult"],
                   "note": "ledger 1,059,840 = 529,920 spatial MACs x MTP positions m=2 (one weight read feeds 2 MAC "
                           "lanes); 529,920 / 32 = 16,560 block-dot lanes"},
        "sharing_factor_latency": {str(s): {"striped_expected_cycles": s * per_macro(tot_exp),
                                            "striped_worst_cycles": s * per_macro(tot_worst)} for s in (1, 2, 4)},
    }
    a.output.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: rec[k] for k in ("per_expert_per_die", "active_experts_on_die", "rom_words_per_token",
                                          "read_floor_cycles_per_token", "budget", "die_totals_sharing_1",
                                          "sharing_factor_latency")}, indent=1))


if __name__ == "__main__":
    main()
