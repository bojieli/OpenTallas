#!/usr/bin/env bash
set -euo pipefail
out=${1:-bench_s8_arf1};mkdir -p "$out"
srcs=(rtl/qwen_dv/s5/s8/qfd_dv_s8_fdn_arf1.sv rtl/qwen_dv/s5/s8/qfd_dv_s8_kept.sv rtl/qwen_dv/s5/s6/qfd_dv_s6_leaves.sv rtl/test/qwen_dv/s8/tb_arf1.sv)
iverilog -g2012 -s tb_arf1 -o "$out/primary" "${srcs[@]}" > "$out/build.log" 2>&1
vvp "$out/primary" > "$out/primary.log" 2>&1
sed "s/arf_wm1_d=cmd_q\[22:7\]-16'd1/arf_wm1_d=cmd_q[22:7]-16'd2/" "${srcs[0]}" > "$out/earlylast.sv"
iverilog -g2012 -s tb_arf1 -o "$out/mut_last" "$out/earlylast.sv" "${srcs[@]:1}" > "$out/build_last.log" 2>&1
if vvp "$out/mut_last" > "$out/last.log" 2>&1;then echo 'LAST MUTANT ESCAPED';exit 1;fi
cat "$out/primary.log" "$out/last.log";echo 'PASS expected last mutant caught'
