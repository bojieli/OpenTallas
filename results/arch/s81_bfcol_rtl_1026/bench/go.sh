#!/bin/bash
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
W=/srv/opentallas-scratch2/claude/wt/s81-bfcol-rtl; R=/srv/opentallas-scratch2/claude/s81-bfcol-rtl
cd $R/bench
verilator --version > vver.txt
bash run_bench.sh $R/gold gold 30000 > gold.rc 2>&1 &
bash run_bench.sh $W gate 30000 > gate.rc 2>&1 &
bash run_bench.sh $R/mut mutant 30000 > mutant.rc 2>&1 &
wait
