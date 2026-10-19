#!/bin/bash
# Q-H16C heads bench (fleet): w130 positive, default positive, MUT 8/9, IBMUT 1. Run from src root.
set -u; O=${O:-../out}; rm -rf $O; mkdir -p $O
"$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" --version
JOBS=8 rtl/test/qwen_dv/run_heads.sh $O/heads_pos -GHD_W130=1 > $O/heads_pos.out 2>&1 &
JOBS=8 rtl/test/qwen_dv/run_heads.sh $O/heads_pos0 > $O/heads_pos0.out 2>&1 &
JOBS=8 rtl/test/qwen_dv/run_heads.sh $O/heads_m8 -GHD_W130=1 -GMUT=8 > $O/heads_m8.out 2>&1 &
JOBS=8 rtl/test/qwen_dv/run_heads.sh $O/heads_m9 -GHD_W130=1 -GMUT=9 > $O/heads_m9.out 2>&1 &
JOBS=8 rtl/test/qwen_dv/run_heads.sh $O/heads_ibmut -GHD_W130=1 -GIBMUT=1 > $O/heads_ibmut.out 2>&1 &
wait
for f in heads_pos heads_pos0 heads_m8 heads_m9 heads_ibmut; do echo "== $f"; cat $O/$f.out; grep -E "^INFO" $O/$f/run.log; done
