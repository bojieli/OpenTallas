#!/bin/bash
# FLEET only. Explicit decoder boundary, actual word-provider SRAM and core guard.
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd);R=$(cd "$D/../../.." && pwd)
W=${1:?work};mkdir -p "$W"
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$VL" --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_mu_cold_provider -Mdir "$W/obj" -o sim \
 "$D/tb_mu_cold_provider.sv" "$R/rtl/qwen_split/qfd_embedding_word_provider.sv" \
 "$R/rtl/qwen_sys/static_embedding_20261014/qkd_embedding_static_preload_face.sv" \
 "$R/rtl/qwen_sys/static_embedding_20261014/qkd_embedding_static_core_store.sv" \
 "$R/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v" >"$W/build.log" 2>&1
"$W/obj/sim" +MODE=0 >"$W/late.log";cat "$W/late.log";grep -q '^COLD_PROVIDER_LATE_PREFIX_DETECTED' "$W/late.log"
"$W/obj/sim" +MODE=1 >"$W/early.log";cat "$W/early.log";grep -q '^COLD_PROVIDER_EARLY_PREFETCH_PASS' "$W/early.log"
