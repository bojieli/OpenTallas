#!/usr/bin/env bash
set -uo pipefail
out=${1:?output}; mkdir -p "$out"
mut=${QSEAT_MUT:-0}
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
verilator --version
verilator --binary --timing -j 4 -Wno-fatal --top-module tb_native59_qseat_sram -GMUT="$mut" \
 -Mdir "$out/obj" rtl/test/qwen_split/tb_native59_qseat_sram.sv rtl/qwen_split/qfd_native59_qseat_sram.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_32x512_m1/ot_sram_1r1w_32x512_m1.v > "$out/build.log" 2>&1 || { tail -30 "$out/build.log";exit 2; }
"$out/obj/Vtb_native59_qseat_sram" > "$out/sim.log" 2>&1
rc=$?
grep -E '^QSEAT_(ERR|PASS|FAIL)' "$out/sim.log"
exit "$rc"
