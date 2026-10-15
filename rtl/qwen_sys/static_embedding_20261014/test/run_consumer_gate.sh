#!/usr/bin/env bash
set -euo pipefail
repo=$(cd "$(dirname "$0")/../../../.." && pwd)
images=${1:?released HBM image directory}
build=${2:?build directory}
mkdir -p "$build"
verilator --binary --timing -Wno-fatal --top-module tb_static_embed_consumer -j 4 --Mdir "$build/obj" \
 "$repo/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v" \
 "$repo/rtl/hdc/ot_hdc_qwen_int8_embed_decode.sv" \
 "$repo/rtl/qwen_sys/static_embedding_20261014/ot_qfd_su_embed_static.sv" \
 "$repo/rtl/qwen_sys/static_embedding_20261014/test/tb_static_embed_consumer.sv" >"$build/build.log" 2>&1
for token in 0 63 64 511 512 65535 65536 151935;do
 python3 "$repo/tools/qwen_embedding_static_vectors.py" "$images" "$token" "$build/vectors_$token"
 "$build/obj/Vtb_static_embed_consumer" +VECTORS="$build/vectors_$token" +TOKEN="$token" >"$build/token_$token.log" 2>&1
done
for mutant in 1 2 3;do
 if "$build/obj/Vtb_static_embed_consumer" +VECTORS="$build/vectors_64" +TOKEN=64 +MUT="$mutant" >"$build/mutant_$mutant.log" 2>&1;then
  echo "FAIL mutant $mutant escaped";exit 1
 fi
done
echo 'PASS eight released full rows with mapped SRAM and three failing schedule/identity mutants'
