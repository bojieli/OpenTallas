#!/bin/bash
cd "$(dirname "$0")"; mkdir -p out; rm -f out/done.txt
r(){ n=$1;shift; python3 src/tools/qwen_static_kv/$1 out/$n "${@:2}" > out/$n.log 2>&1; echo "$n rc=$?" >> out/done.txt; }
for pc in $(seq 0 31); do r rr_pc$pc run_refresh_context_controller.py --pc $pc & done
for m in 1 2 3 4 5; do r rr_m${m} run_refresh_context_controller.py --pc 13 --mutant $m & done
r fr_m0 run_context_front.py --mutant 0 &
for m in 0 1 2 3 4 10; do r fr_m${m}_l12s24 run_context_front.py --mutant $m --late 12 --strag 24 & done
wait; sort -V out/done.txt
