#!/bin/bash
set -euo pipefail
out=$1
mkdir -p "$out"
iverilog -g2012 -s tb_qkh_ingress_n4 -o "$out/tb" rtl/test/qwen_split/tb_qkh_ingress_n4.sv rtl/qwen_sys/split_20261014/qkh_head_ingress_abc.sv rtl/qwen_sys/split_20261014/qkh_head_stages.sv rtl/qwen_sys/split_20261014/qkh_head_gather_stage.sv
vvp "$out/tb" > "$out/positive.log" 2>&1
for mutant in 31 32 33 41 42 43; do
 if vvp "$out/tb" +negative="$mutant" > "$out/mutant-$mutant.log" 2>&1; then echo "MUTANT_ESCAPE $mutant";exit 1;fi
 grep -q N4_INGRESS_FAIL "$out/mutant-$mutant.log"
done
cat "$out/positive.log"
echo N4_INGRESS_SIX_MUTANTS_REJECTED
