#!/bin/bash
set -eu
out=$1
mkdir -p "$out"
for mut in 0 1;do
 iverilog -g2012 -s tb_b2_train_source -Ptb_b2_train_source.MUT=$mut -o "$out/sim$mut" rtl/qwen_split/qfd_b2_train_source.sv tools/qwen_b2_join/tb_b2_train_source.sv > "$out/build$mut.log" 2>&1
 if vvp "$out/sim$mut" > "$out/run$mut.log" 2>&1;then test "$mut" = 0;else test "$mut" = 1;fi
done
cat "$out/run0.log"
