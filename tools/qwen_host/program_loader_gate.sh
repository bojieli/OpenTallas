#!/usr/bin/env bash
set -euo pipefail
R=$(cd "$(dirname "$0")/../.." && pwd)
OUT=$1; MUT=${2:-0}; mkdir -p "$OUT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --binary --timing -j 4 -Wno-fatal --top-module tb_qkd_host_program_loader -GMUT="$MUT" --Mdir "$OUT/obj" "$R/rtl/test/qwen_host/tb_qkd_host_program_loader.sv" "$R/rtl/qwen_sys/host_20261013/qkd_host_program_loader.sv" "$R/physical/asap7_memory_macros/ot_sram_1rw_256x64_m4_r2c2/ot_sram_1rw_256x64_m4_r2c2.v" "$R/rtl/physical/ot_qwen_host_ctl.sv" "$R/rtl/qwen_sys/system_20261008/ot_qfd_pkgctl.sv" > "$OUT/build.log" 2>&1
"$OUT/obj/Vtb_qkd_host_program_loader" > "$OUT/run.log" 2>&1
cat "$OUT/run.log"
