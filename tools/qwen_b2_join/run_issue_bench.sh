#!/bin/bash
set -eu
out=$1
mkdir -p "$out"
for mut in 0 1 3; do
 iverilog -g2012 -s tb_b2_issue -Ptb_b2_issue.MUT=$mut -o "$out/sim$mut" rtl/qwen_split/qfd_res_train_issue_b2.sv tools/qwen_b2_join/tb_b2_issue.sv > "$out/build$mut.log" 2>&1
 if vvp "$out/sim$mut" > "$out/run$mut.log" 2>&1; then
  test "$mut" = 0
 else test "$mut" != 0; fi
done
cat "$out/run0.log"
