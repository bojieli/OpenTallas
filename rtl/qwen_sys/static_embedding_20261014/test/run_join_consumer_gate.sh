#!/usr/bin/env bash
set -euo pipefail
ulimit -c 0
repo=$(cd "$(dirname "$0")/../../../.." && pwd)
build=${1:?build directory};vectors=${2:?vectors root}
mkdir -p "$build"
cd "$repo"
base=rtl/qwen_sys/static_embedding_20261014
verilator --binary --timing -Wno-fatal --top-module tb_static_embed_join_consumer -j 4 --Mdir "$build/obj" \
 "$base/test/tb_static_embed_join_consumer.sv" "$base/qkd_embedding_static_join.sv" \
 "$base/qkd_embedding_static_preload_face.sv" "$base/ot_qfd_su_embed_static.sv" \
 rtl/hdc/ot_hdc_qwen_int8_embed_decode.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v >"$build/build.log" 2>&1
for token in 0 63 64 511 512 65535 65536 151935;do
 "$build/obj/Vtb_static_embed_join_consumer" +VECTORS="$vectors/vectors_$token" +TOKEN="$token" >"$build/token_$token.log" 2>&1
done
for mutant in 1 2;do
 if "$build/obj/Vtb_static_embed_join_consumer" +VECTORS="$vectors/vectors_64" +TOKEN=64 +MUT="$mutant" >"$build/mutant_$mutant.log" 2>&1;then echo "FAIL mutant $mutant escaped";exit 1;fi
done
echo 'PASS real join+epoch face+mappedSRAM consumer eight full released rows and failing epoch/availability mutants'
