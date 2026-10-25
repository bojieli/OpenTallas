#!/bin/bash
cd /m
run() { tag=$1; stn=$2; al=$3; lo=$4
 verilator --binary -j 8 --timing -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -O2 --top-module miter_tb -GSTN=$stn -GQB_ALIGN=$al -GQB_LOCAL32=$lo -GCYCLES=${CYCLES:-200000} -GSEED=1 -Mdir obj_$tag old_qbank.sv new_macro.v new_qbank.sv miter_tb.sv > build_$tag.log 2>&1 || { echo "$tag BUILD FAIL"; grep -m5 -i error build_$tag.log; return; }
 ./obj_$tag/Vmiter_tb > run_$tag.log; grep -E "MITER|MISMATCH" run_$tag.log | head -3 | sed "s/^/$tag: /"; rm -rf obj_$tag; }
run stn_a0l0 1 0 0 &
run stn_a1l1 1 1 1 &
run mut_a0l0 2 0 0 &
run mut3_a0l0 3 0 0 &
wait
