#!/bin/bash
set -euo pipefail
cd "${1:?runtime}"
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
for rt in 171 173; do
 cp prog$rt.hex prog.hex
 for fmt in 0 1; do
  tag=${rt}_$fmt
  verilator --binary --timing --build-jobs 2 -j 2 -Wno-fatal -Wno-lint -Wno-style --top-module tb_idx_rows_numeric -GRT=$rt -GLEN=$((1395+rt)) -GWFP32=$fmt --Mdir obj$tag -o tb *.sv *.v > build$tag.log 2>&1
  ./obj$tag/tb > run$tag.log 2>&1 || { tail -10 run$tag.log;exit 1; }
  grep IDX_NUMERIC_PASS run$tag.log
  if [ "$fmt" = 1 ]; then
   for mut in BAD_WEIGHT WRONG_STRIDE; do
    if ./obj$tag/tb +$mut > mut${tag}_$mut.log 2>&1; then echo "MUTANT_SURVIVED $tag $mut";exit 1;fi
    grep IDX_NUMERIC_FAIL mut${tag}_$mut.log
   done
  fi
 done
done
