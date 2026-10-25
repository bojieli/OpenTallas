#!/bin/bash
# usage: run_miter.sh <dir with old_qbank.sv old_macro.v new_qbank.sv new_macro.v miter_tb.sv> ; runs in verilator/verilator:v5.032
set -u
cd "$1"
run() { # tag qbank macro align local32
  local tag=$1 qb=$2 mac=$3 al=$4 lo=$5
  rm -rf obj_$tag
  verilator --binary -j 8 --timing -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -O2 --top-module miter_tb \
    -GQB_ALIGN=$al -GQB_LOCAL32=$lo -GCYCLES=${CYCLES:-100000} -GSEED=${SEED:-1} -Mdir obj_$tag \
    old_macro.v old_qbank.sv $mac $qb miter_tb.sv > build_$tag.log 2>&1 || { echo "$tag BUILD FAIL"; tail -20 build_$tag.log; return; }
  ./obj_$tag/Vmiter_tb | tee run_$tag.log | grep -E "MITER|MISMATCH" | head -3 | sed "s/^/$tag: /"
  rm -rf obj_$tag
}
run nom_a0l0 new_qbank.sv new_macro.v 0 0
run nom_a1l0 new_qbank.sv new_macro.v 1 0
run nom_a1l1 new_qbank.sv new_macro.v 1 1
run mut_rtl_a1l1 mut_rtl_qbank.sv new_macro.v 1 1
run mut_mac_a1l1 new_qbank.sv mut_macro.v 1 1
