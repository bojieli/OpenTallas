#!/bin/bash
# Qwen ROM 8K DSpark verdict with the r21 die relay stations charged (2026-10-07); run from the repository root.
# Same inputs/method as results/rtl/qwen_rom_kv_fullbw_20261004/dspark_verdict.json (reproduced byte-identical without
# --relays apart from the method text); --ar-cycles = results/arch/three_machine_compose/compose.json qwen_rom.token_cycles.
R=results/rtl/qwen_rom_kv_fullbw_20261004
python3 tools/qwen_rom_dspark_verdict.py \
  --verify baseline_np4:4:17197:$PWD/$R/dspark_verify_P8187/result.json \
  --verify merge_su_np2:2:9942:$PWD/$R/dspark_verify_merge/k_m2/result.json \
  --verify merge_su_np3:3:13104:$PWD/$R/dspark_verify_merge/k_m3/result.json \
  --verify merge_su_np4:4:15971:$PWD/$R/dspark_verify_merge/k_m4/result.json \
  --relays results/rtl/qwen_rom_die_r17_20261005/relays_r21/relay_token_cost.json \
  --ar-cycles 216713 --extra-per-me-op 1 --extra-per-step 54 \
  --out results/rtl/qwen_rom_die_r17_20261005/relays_r21/dspark_verdict_relays.json
