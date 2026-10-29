#!/bin/bash
set -euo pipefail
cd "${1:?runtime}"
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
for rt in 171 173; do
 len=$((1395+rt))
 cp prog$rt.hex prog.hex
 verilator --binary --timing --build-jobs 2 -j 2 -Wno-fatal -Wno-lint -Wno-style --top-module tb_idx_rows_numeric -GRT=$rt -GLEN=$len --Mdir obj$rt -o tb *.sv *.v > build$rt.log 2>&1
 ./obj$rt/tb > run$rt.log 2>&1 || { tail -10 run$rt.log;exit 1; }
 grep IDX_NUMERIC_PASS run$rt.log
 for mut in DROP_CLEAR WRONG_STRIDE DROP_RETURN; do
  if ./obj$rt/tb +$mut > mut${rt}_${mut}.log 2>&1; then echo "MUTANT_SURVIVED $rt $mut";exit 1;fi
  grep IDX_NUMERIC_FAIL mut${rt}_${mut}.log
 done
done
