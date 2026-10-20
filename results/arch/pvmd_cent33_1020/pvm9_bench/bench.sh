#!/bin/bash
# PVM9 benches: gold + async/causal mutants on Verilator 5.050 (daemon pin)
cd /srv/opentallas-scratch/claude/pvm9-1020/src
B=rtl/hbm_accel/sm/attn/test/run_pv_merge_distributed_bench.sh
O=/srv/opentallas-scratch/claude/pvm9-1020/bench; mkdir -p $O
run(){ n=$1; shift; bash $B $O/$n "$@" > $O/$n.out 2>&1; echo "$n rc=$? $(tail -1 $O/$n.out)"; }
run exact 0 2 0 0 0 0 1 & run stopx 0 2 0 0 2 1 1 & run legacy 0 2 0 0 0 0 0 & run tight 0 2 1 0 0 0 1 &
run reassert1 0 2 0 0 1 0 1 & run mut4 4 2 0 0 0 0 1 & run mut14 14 2 0 0 2 0 1 & run mut15 15 2 0 0 0 0 1 & run mut16 16 2 0 0 2 0 1 &
wait
