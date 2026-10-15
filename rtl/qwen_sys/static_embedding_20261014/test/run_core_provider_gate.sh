#!/usr/bin/env bash
set -euo pipefail
ulimit -c 0
repo=$(cd "$(dirname "$0")/../../../.." && pwd)
build=${1:?build}; vectors=${2:?vectors151935}
mkdir -p "$build";cd "$repo"
base=rtl/qwen_sys/static_embedding_20261014
verilator --binary --timing -Wno-fatal -j 4 --Mdir "$build/obj" --top-module tb_static_embed_core_provider "$base/test/tb_static_embed_core_provider.sv" "$base/qkd_embedding_static_core_provider.sv" "$base/qkd_embedding_static_core_store.sv" "$base/qkd_embedding_static_join.sv" "$base/qkd_embedding_static_preload_face.sv" physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v >"$build/build.log" 2>&1
"$build/obj/Vtb_static_embed_core_provider" +VECTORS="$vectors" +TOKEN=151935 >"$build/positive.log" 2>&1
for mut in 1 2;do
 if "$build/obj/Vtb_static_embed_core_provider" +VECTORS="$vectors" +TOKEN=151935 +MUT="$mut" >"$build/mutant_$mut.log" 2>&1;then echo 'FAIL producer mutant escaped';exit 1;fi
done
echo 'PASS actual join+epochface+core SRAM provider and two producer mutants'
