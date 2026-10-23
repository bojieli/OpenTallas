#!/usr/bin/env bash
set -euo pipefail
out=$1
mkdir -p "$out"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version > "$out/version.txt"
verilator --binary --timing -j 4 -O2 -Wno-fatal -Wno-lint -Wno-style --top-module tb_tap_bounded --Mdir "$out/obj" rtl/test/qwen_dv/s8/tb_tap_bounded.sv rtl/qwen_dv/s5/s6/qfd_dv_s6_leaves.sv rtl/qwen_dv/s5/s8/qfd_dv_s8_tap_bounded.sv rtl/qwen_dv/s5/s8/qfd_dv_s8_tap_bounded_helpers.sv > "$out/build.log" 2>&1
"$out/obj/Vtb_tap_bounded" > "$out/primary.log" 2>&1
cat "$out/primary.log"
if "$out/obj/Vtb_tap_bounded" +mutant=1 > "$out/mutant.log" 2>&1;then echo 'MUTANT ESCAPED';exit 1;fi
grep TAP_BOUNDED_MISMATCH "$out/mutant.log"
