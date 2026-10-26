#!/usr/bin/env bash
# ELEM-CENSUS 2026-10-16: standalone bench of qfd_embedding_word_provider (tb_qfd_embedding_word_provider.sv).
# usage: run_embedding_word_provider_bench.sh OUTDIR [MUT]
#   MUT 0: the shipped RTL, must print EMB_PROVIDER_PASS.
#   Mutants are made on COPIES of the two child sources in OUTDIR (the shipped RTL is never edited), each must FAIL:
#   MUT 1: core store drops the row-complete check on core_start (an incomplete row would be served)
#   MUT 2: core store writes the row SRAM at word index ^ 1 (code words swapped in the mapped SRAM)
#   MUT 3: core store latches the BF16 scale from the wrong half of the header word
set -euo pipefail
out=${1:?fresh output directory}; mut=${2:-0}; mkdir -p "$out"
R=$(cd "$(dirname "$0")/../../.." && pwd)
FACE=$R/rtl/qwen_sys/static_embedding_20261014/qkd_embedding_static_preload_face.sv
STORE=$R/rtl/qwen_sys/static_embedding_20261014/qkd_embedding_static_core_store.sv
cp "$FACE" "$out/face.sv"; cp "$STORE" "$out/store.sv"
case "$mut" in
  0) ;;
  1) sed -i 's/if(core_start&&(!complete||/if(core_start\&\&(/' "$out/store.sv" ;;
  2) sed -i 's/\.w_addr_in(preload_word)/.w_addr_in(preload_word^6'"'"'d1)/' "$out/store.sv" ;;
  3) sed -i 's/scale<=preload_data\[15:0\]/scale<=preload_data[31:16]/' "$out/store.sv" ;;
  *) echo "unknown MUT $mut"; exit 2 ;;
esac
if [ "$mut" != 0 ] && cmp -s "$out/face.sv" "$FACE" && cmp -s "$out/store.sv" "$STORE"; then
  echo "MUTANT_NOT_APPLIED $mut"; exit 2; fi
iverilog -g2012 -s tb_qfd_embedding_word_provider -o "$out/sim.vvp" \
  "$R/rtl/test/qwen_split/tb_qfd_embedding_word_provider.sv" "$R/rtl/qwen_split/qfd_embedding_word_provider.sv" \
  "$out/face.sv" "$out/store.sv" \
  "$R/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v" > "$out/build.log" 2>&1 \
  || { echo BUILD_FAILED; tail -20 "$out/build.log"; exit 2; }
vvp -n "$out/sim.vvp" 2>&1 | tee "$out/result.log"
grep -q '^EMB_PROVIDER_PASS' "$out/result.log"
