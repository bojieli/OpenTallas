#!/bin/bash
set -euo pipefail
out=$1
mkdir -p "$out"
if [ "$#" -ge 2 ];then
  mutant=$2
  iverilog -g2012 -s tb_qkh_head_gather -Ptb_qkh_head_gather.MUT="$mutant" \
    -o "$out/tb-$mutant" rtl/test/qwen_split/tb_qkh_head_gather.sv \
    rtl/qwen_sys/split_20261014/qkh_head_gather_stage.sv \
    rtl/qwen_sys/split_20261014/qkh_head_stages.sv
  vvp "$out/tb-$mutant"
  exit "$?"
fi
for mutant in 0 41 42 43; do
  iverilog -g2012 -s tb_qkh_head_gather -Ptb_qkh_head_gather.MUT="$mutant" \
    -o "$out/tb-$mutant" rtl/test/qwen_split/tb_qkh_head_gather.sv \
    rtl/qwen_sys/split_20261014/qkh_head_gather_stage.sv \
    rtl/qwen_sys/split_20261014/qkh_head_stages.sv
  if vvp "$out/tb-$mutant" > "$out/mutant-$mutant.log" 2>&1; then
    if [ "$mutant" != 0 ];then echo "MUTANT_ESCAPE $mutant";exit 1;fi
  else
    if [ "$mutant" = 0 ];then cat "$out/mutant-$mutant.log";exit 1;fi
    grep -q GATHER_FAIL "$out/mutant-$mutant.log"
  fi
done
cat "$out/mutant-0.log"
echo GATHER_THREE_DUT_MUTANTS_REJECTED
