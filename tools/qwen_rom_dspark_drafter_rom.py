#!/usr/bin/env python3
"""Qwen3-8B ROM die: DSpark drafter ROM placement, area and time-multiplexed draft step (model only).

Inputs (all pinned below by value with their source):
  * drafter checkpoint facts: results/rtl/qwen_rom_dspark_20261003/drafter/drafter_facts.json
    (deepseek-ai/dspark_qwen3_8b_block7; embed_tokens and lm_head are the target's);
  * the TP4 W12 tile: 1,536 tiles a die, 4 groups x 16 lanes, CODE_BANKS 5 banks of two
    ot_rom_4096x266_m8 macros (rtl/test/qwen_rom_runtime/qwen_rom_rt_w12.cpp: rom_addr = bank*4096 + addr,
    one 512-bit word a tile a cycle), r2 floorplan ROMS_PER_TILE 10
    (results/uarch/qwen_rom_floorplan_nearhbm_20261003/model-r2.json @ ced04cd96);
  * target code words a die: 36 layers x 512 (qkv 64 + o 48 + gate/up 256 + down 144; layer0_rom.json
    matrix_layout code_span_words) + lm_head 1,584 (head_rom.json) = 20,016 of 5 x 4,096 = 20,480;
  * macro catalog physical/asap7_memory_macros/index.json: ot_rom_4096x266_m8 7,663.948 um2,
    SS fmax 1,414 MHz; ot_rom_8192x266_m8 14,590.031 um2, SS fmax 1,017.5 MHz (fails 1.2 GHz);
    tile macro pack 1.31 (tools/uarch_model.py QWEN_AREA);
  * floorplan r2 budget: die 792.0 mm2, 23.0 under 815; free shoreline 20.29, IO spare 9.11.

Draft step (time-multiplexed on the tile array, the target's own engine), per step:
  ingest   fc (20,480 -> 4,096, rows split by die) for the n_ctx newly committed tokens, all-gather of the
           1,024-row slices (the K/V projections need the whole context feature), hidden_norm, then the
           context K/V projections of every drafter layer for those tokens;
  block    5 drafter layers over S slot positions: one target-shaped layer each (measured TP4 layer
           3,930 cycles at one position) plus the per-extra-position increment of the verify layer;
  lm_head  base logits of the S slots: 1,584 issue a slot a die (the target's head, shared);
  markov   sequential over slots: w2 (151,936 x 256) bias of the previous token, the add + argmax over
           the die's 37,984 rows on the stream unit, then the cross-die argmax all-gather.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REC = ROOT / "results/rtl/qwen_rom_dspark_20261003/drafter"

TP, TILES, WORD_BYTES = 4, 1536, 6144 * 16          # one code word: 6,144 groups x 16 lanes x INT8
BANK_WORDS, BANKS = 4096, 5
TARGET_WORDS = 36 * (64 + 48 + 256 + 144) + 1584     # 20,016
MACRO_4096_UM2, MACRO_8192_UM2, PACK = 7663.948, 14590.031, 1.31
MACRO_SS_FMAX = {"ot_rom_4096x266_m8": 1414.2, "ot_rom_8192x266_m8": 1017.5}
DIE_R2, BUDGET, SHORE_FREE, IO_SPARE = 792.0, 815.0, 20.29, 9.11
ROM_BYTES_PER_MM2 = 4096 * 256 / 8 / (MACRO_4096_UM2 * PACK / 1e6)   # data bits of a packed 4096x266 macro

# measured / pinned timing terms (cycles at 1.2 GHz)
LAYER_P1 = 3930            # TP4 layer, one-stream all-reduce (claude/qwen-allreduce-oneseg-20261003 @ 7d736e8e6)
ME_ISSUE_LAYER = 512       # code words a layer = ME issue cycles
HEAD_ISSUE = 1584          # lm_head issue a position a die
LINK_LAT = 339             # collective link latency (runtime --coll-lat)
AR_ONESTREAM = 624         # one 256-word all-reduce, measured (verilator_gate.json)
SU_WIDTH = 64
ME_FIXED = 16 + 112 + 60   # fill + wire stages + tree (pricing basis: 188-336 fixed per op; low end)
# per extra verify position, per layer: pricing.json increment_per_extra_position_per_layer (MODEL until the
# step-1 RTL gate measures it: claude/qwen-rom-dspark-20261003)
INC = {"existing_rtl": 3749, "widened_ar": 3013, "widened_ar_attn2_overlap": 1140}


def words(params_per_die):
    return -(-int(params_per_die) // WORD_BYTES)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=REC / "drafter_rom_schedule.json")
    a = ap.parse_args()
    facts = json.loads((REC / "drafter_facts.json").read_text())
    g = facts["params_by_group"]
    layer_words = 5 * ME_ISSUE_LAYER                  # same shape as a target layer: same packing
    fc_words = words(g["fc"] / TP)
    w2_words = words(g["markov_head"] / 2 / TP)       # w2 rows split by vocabulary like lm_head
    w1_bytes_die = g["markov_head"] / 2               # w1 replicated per die (a 256-byte row lookup)
    tile_words = layer_words + fc_words + w2_words
    slack = BANKS * BANK_WORDS - TARGET_WORDS
    extra = tile_words - slack
    banks_needed = -(-extra // BANK_WORDS)
    opt_a_mm2 = TILES * banks_needed * 2 * MACRO_4096_UM2 * PACK / 1e6
    # 8192-row re-bank: 3 banks (24,576 words) of 2 macros instead of 5 x 4096 -- fails SS 1.2 GHz
    opt_b_mm2 = TILES * (3 * 2 * MACRO_8192_UM2 - BANKS * 2 * MACRO_4096_UM2) * PACK / 1e6
    w1_mm2 = w1_bytes_die / ROM_BYTES_PER_MM2
    w1_split_mm2 = w1_mm2 / TP
    die_a = DIE_R2 + opt_a_mm2
    rom = {
        "drafter_unique_params": facts["drafter_unique_params"],
        "tile_code_words_per_die": {"5_layers": layer_words, "fc": fc_words, "markov_w2": w2_words, "total": tile_words},
        "target_code_words_per_die": TARGET_WORDS, "tile_capacity_words": BANKS * BANK_WORDS, "tile_slack_words": slack,
        "extra_words_beyond_slack": extra, "extra_4096_banks_per_tile": banks_needed,
        "extra_bank_fill": round(extra / (banks_needed * BANK_WORDS), 3),
        "option_a_plus_one_4096_bank": {"mm2_per_die": round(opt_a_mm2, 2), "macros_per_tile": 2 * banks_needed,
                                        "macro_ss_fmax_mhz": MACRO_SS_FMAX["ot_rom_4096x266_m8"], "closes_1p2ghz": True,
                                        "die_mm2": round(die_a, 1), "over_815_mm2": round(die_a - BUDGET, 1),
                                        "reticle_26x33": "width 24.147 -> %.2f mm at 32.8 mm height" % (die_a / 32.8)},
        "option_b_rebank_8192": {"mm2_per_die": round(opt_b_mm2, 2), "macro_ss_fmax_mhz": MACRO_SS_FMAX["ot_rom_8192x266_m8"],
                                 "closes_1p2ghz": False, "verdict": "rejected: SS fmax 1,017.5 MHz < 1,200"},
        "markov_w1": {"bytes_per_die_replicated": int(w1_bytes_die), "mm2_replicated": round(w1_mm2, 2),
                      "mm2_split_by_rank": round(w1_split_mm2, 2), "home": "IO-edge ROM beside the embedding ROM (IO spare 9.11)",
                      "split_costs": "a 256-element all-gather a slot (~2 x 339 link cycles) on the sequential chain"},
        "markov_pricing_correction": {"pricing_mm2": 1.13, "w2_home": "tile bank (part of option A)",
                                      "w1_mm2": round(w1_mm2, 2), "note": "pricing counted one of the two 151,936 x 256 matrices"},
        "fit_verdict": ("does NOT fit r2 at 815 mm2: the drafter must sit in the tiles that consume it (a word a tile a "
                        "cycle), so the free shoreline (20.29) and IO spare (9.11) cannot host it; +1 bank of two "
                        "4096x266 macros per tile = %.2f mm2 makes the die %.1f mm2 (%.1f over). The pricing's "
                        "'fits r2 slack ~52' treated shoreline/IO area as fungible with tile ROM." % (opt_a_mm2, die_a, die_a - BUDGET)),
    }

    def step(S, n_ctx, inc):
        ingest = n_ctx * fc_words + ME_FIXED + AR_ONESTREAM + 5 * (2 * 21 * n_ctx + ME_FIXED)
        block = 5 * (LAYER_P1 + (S - 1) * inc)
        head = S * HEAD_ISSUE + ME_FIXED
        markov_slot = w2_words + ME_FIXED + -(-37984 // SU_WIDTH) + 50 + 2 * LINK_LAT + 8
        markov = S * markov_slot
        return {"S": S, "n_ctx": n_ctx, "ingest": ingest, "block": block, "lm_head": head,
                "markov_per_slot": markov_slot, "markov": markov, "total": ingest + block + head + markov,
                "us_at_1p2ghz": round((ingest + block + head + markov) / 1200, 2)}

    sched = {k: [step(S, n, inc) for S, n in ((3, 3), (7, 4))] for k, inc in INC.items()}
    rec = {"schema": "opentallas.qwen-rom-dspark-drafter-rom.v1", "status": "MODEL_ONLY", "rom": rom,
           "draft_step_cycles": sched,
           "draft_step_basis": {"layer_p1": LAYER_P1, "per_extra_position_increment": INC,
                                "increment_status": "MODEL (pricing.json); replace with the step-1 measured verify-layer increment",
                                "ctx_kv_proj_words_per_token_per_layer": 21, "me_fixed": ME_FIXED,
                                "allgather_ctx_feature": AR_ONESTREAM, "su_width": SU_WIDTH, "link_lat": LINK_LAT},
           "target_ar_token_cycles": 202590,
           "sources_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in (
               "tools/qwen_rom_dspark_drafter_rom.py", "results/rtl/qwen_rom_dspark_20261003/drafter/drafter_facts.json",
               "physical/asap7_memory_macros/index.json", "tools/uarch_model.py")},
           "claim_boundary": "Placement/area/schedule model from pinned constants; no RTL, no P&R. Draft block term uses the "
                             "MODEL verify-layer increment until step 1 measures it."}
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({"rom": {k: rom[k] for k in ("tile_code_words_per_die", "extra_words_beyond_slack", "option_a_plus_one_4096_bank")},
                      "steps": {k: [(s["S"], s["total"], s["us_at_1p2ghz"]) for s in v] for k, v in sched.items()}}, indent=1))


if __name__ == "__main__":
    main()
