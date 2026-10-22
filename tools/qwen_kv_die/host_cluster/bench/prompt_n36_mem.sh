#!/bin/bash
set -eu
OUT=${1:-out};mkdir -p "$OUT"
verilator --version
MODES=${2:-"pass wide bypass addr"}
# QE3-HROOT-PROMPT 10-21: 3rd arg "r" runs the same suite on the registered-read ot_hkv_prompt_mem_r (prompt_safe5);
# its causal mutants are "bypass" -> OT_PROMPT_MUT_VIS (visibility ignores the older in-flight enqueue) and "addr".
TB=tb_hkv_prompt_mem;DUT=rtl/qwen_sys/host_cluster_20261017/prompt_safe/ot_hkv_prompt_mem.sv;BYP=-DOT_PROMPT_MUT_BYPASS
if [ "${3:-}" = r ];then TB=tb_hkv_prompt_mem_r;DUT=rtl/qwen_sys/host_cluster_20261017/prompt_safe5/ot_hkv_prompt_mem_r.sv;BYP=-DOT_PROMPT_MUT_VIS;fi
for mode in $MODES;do
 defs=();[ "$mode" != wide ]||defs=(-GW=512 -GA=2);[ "$mode" != bypass ]||defs=($BYP);[ "$mode" != addr ]||defs=(-DOT_PROMPT_MUT_ADDR)
 verilator --binary --timing -j 4 -Wno-fatal "${defs[@]}" --top-module $TB -Mdir "$OUT/$mode" rtl/test/qwen_host/$TB.sv $DUT physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1_p192_mir/ot_sram_1r1w_32x546_m1_p192_mir.v >"$OUT/$mode.build.log" 2>&1
 set +e
 "$OUT/$mode/V$TB" >"$OUT/$mode.log" 2>&1
 rc=$?
 set -e
 if [ "$MODES" = addr ]||[ "$MODES" = bypass ];then cat "$OUT/$mode.log";exit "$rc";fi
 if [ "$mode" = pass ]||[ "$mode" = wide ];then [ "$rc" = 0 ];else [ "$rc" != 0 ];fi
 cat "$OUT/$mode.log"
done
grep -q 'PROMPT_MEM PASS' "$OUT/pass.log"
grep -q 'PROMPT_MEM PASS' "$OUT/wide.log"
grep -q 'PROMPT_MEM FAIL' "$OUT/bypass.log"
grep -q 'PROMPT_MEM FAIL' "$OUT/addr.log"
echo 'PROMPT_MEM_SUITE PASS 2 positive 2 causal mutants'
