#!/bin/bash
set -eu
out=${2:-$PWD/fence_${1:-exact}};mkdir -p "$out"
def=();case "${1:-exact}" in addr)def=(-DFENCE_MUT_ADDR);;bypass)def=(-DFENCE_MUT_BYPASS);;esac
"$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" --binary --timing -Wno-fatal --top-module tb -j 4 --Mdir "$out/obj" "${def[@]}" rtl/lib/ot_reset_sync.sv rtl/physical/ot_host_die_cdc_sram.sv rtl/qwen_sys/host_cluster_cdc_20261018/qkd_hr_visibility_fence_cdc.sv rtl/qwen_sys/host_cluster_cdc_20261018/qkd_hr_visibility_fence_sram.sv physical/asap7_memory_macros/ot_sram_1r1w_32x64_m1_p192_mir/ot_sram_1r1w_32x64_m1_p192_mir.v rtl/test/host_cdc_safe_1020/tb_fence.sv >"$out/build.log" 2>&1
"$out/obj/Vtb" >"$out/run.log" 2>&1
cat "$out/run.log"
