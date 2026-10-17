#!/bin/bash
cd "$(dirname "$0")"
run(){ n=$1;shift; python3 src/tools/qwen_static_kv/run_context_front.py out/$n "$@" > out/$n.log 2>&1; echo "$n rc=$?" >> out/done.txt; }
mkdir -p out; rm -f out/done.txt
run m0_l0 --mutant 0 &
for ls in "0 32" "12 24" "30 0" "36 0"; do set -- $ls; for m in 0 2 3 1 4 10; do run m${m}_l$1s$2 --mutant $m --late $1 --strag $2 & done; done
wait; sort out/done.txt
