#!/bin/bash
set -euo pipefail
OUT=${1:?out};MUT=${2:-0};mkdir -p "$OUT";OUT=$(cd "$OUT"&&pwd)
v=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$v" --version
"$v" --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_program_n37_eq -GMUT="$MUT" --Mdir "$OUT/obj" \
 physical/asap7_memory_macros/ot_sram_1rw_256x64_m4_r2c2/ot_sram_1rw_256x64_m4_r2c2.v \
 rtl/qwen_sys/host_cluster_20261017/prompt_safe6/qkd_host_program_loader_target.sv \
 rtl/test/qwen_host/ref/qkd_host_program_loader_target_n36_ref.sv rtl/test/qwen_host/tb_program_n37_eq.sv >"$OUT/build.log" 2>&1
"$OUT/obj/Vtb_program_n37_eq" | tee "$OUT/run.log"
