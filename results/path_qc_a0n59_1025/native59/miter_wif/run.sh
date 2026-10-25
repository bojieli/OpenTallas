#!/bin/bash
cd /m
run() { tag=$1; qb=$2; al=$3; lo=$4; wif=$5
 verilator --binary -j 8 --timing -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -O2 --top-module miter_tb -GWIF=$wif -GQB_ALIGN=$al -GQB_LOCAL32=$lo -GCYCLES=${CYCLES:-100000} -GSEED=1 -Mdir obj_$tag old_qbank.sv new_macro.v $qb miter_tb.sv > build_$tag.log 2>&1 || { echo "$tag BUILD FAIL"; tail -20 build_$tag.log; return; }
 ./obj_$tag/Vmiter_tb > run_$tag.log; grep -E "MITER" run_$tag.log | sed "s/^/$tag: /"; rm -rf obj_$tag; }
run wif_a0l0 new_qbank.sv 0 0 1 &
run wif_a1l1 new_qbank.sv 1 1 1 &
run off_a1l1 new_qbank.sv 1 1 0 &
run mut_a1l1 mut_qbank.sv 1 1 1 &
wait
