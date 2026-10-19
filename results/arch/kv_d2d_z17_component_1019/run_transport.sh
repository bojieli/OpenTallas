#!/bin/bash
set -eu
mkdir -p out
command -v iverilog
iverilog -V > out/tool.txt 2>&1
for mut in 0 1 2; do
  iverilog -g2012 -s tb -Ptb.MUT=$mut -o out/t$mut ot_kv_z17_transport_private.sv tb_transport.sv
  set +e
  vvp out/t$mut > out/mut$mut.log 2>&1
  rc=$?
  set -e
  if [ "$mut" = 0 ]; then test "$rc" = 0; else test "$rc" != 0; grep -q COHORT_FAIL out/mut$mut.log; fi
done
printf 'MATRIX_PASS positive and two causal mutants\n'
