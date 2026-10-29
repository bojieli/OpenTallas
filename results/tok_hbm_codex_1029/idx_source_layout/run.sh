#!/bin/bash
set -euo pipefail
cd "${1:?runtime}"
qoff=${2:?query sector offset}
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
for rt in 171 173; do
 cp prog$rt.hex prog.hex
 if [ "$rt" = 173 ]; then qsector=$((20480+qoff));else qsector=$((28672+qoff));fi
 verilator --binary --timing --build-jobs 2 -j 2 -Wno-fatal -Wno-lint -Wno-style --top-module tb_idx_rows_numeric -GRT=$rt -GLEN=$((1395+rt)) -GWFP32=1 -GQSECTOR=$qsector --Mdir obj$rt -o tb *.sv *.v > build$rt.log 2>&1
 ./obj$rt/tb > run$rt.log 2>&1 || { tail -10 run$rt.log;exit 1; }
 grep IDX_NUMERIC_PASS run$rt.log
done
