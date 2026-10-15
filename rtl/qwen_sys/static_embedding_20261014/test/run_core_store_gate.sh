#!/usr/bin/env bash
set -euo pipefail
ulimit -c 0
repo=$(cd "$(dirname "$0")/../../../.." && pwd)
build=${1:?build}; vectors=${2:?released token151935 vectors}
mkdir -p "$build"
cd "$repo"
verilator --binary --timing -Wno-fatal -j 4 --Mdir "$build/obj" --top-module tb_static_embed_core_store rtl/qwen_sys/static_embedding_20261014/test/tb_static_embed_core_store.sv rtl/qwen_sys/static_embedding_20261014/qkd_embedding_static_core_store.sv physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v >"$build/build.log" 2>&1
"$build/obj/Vtb_static_embed_core_store" +VECTORS="$vectors" >"$build/positive.log" 2>&1
if "$build/obj/Vtb_static_embed_core_store" +VECTORS="$vectors" +MUT=1 >"$build/address_mutant.log" 2>&1; then echo 'FAIL address mutant escaped';exit 1;fi
echo 'PASS native core store actual SRAM + address mutant'
