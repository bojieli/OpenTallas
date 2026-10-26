#!/bin/bash
# Q-VMWB strict 32-PC + negatives of the STATIC_REFRESH context calendar at codex 6599c1558 (read-only source tree)
SRC=/home/ubuntu/wt/qwen-context-calendar-1016
OUT=/tmp/qvmwb_ctx/b
{ for pc in $(seq 0 31); do echo "pc$pc --pc $pc"; done; for m in 1 2 3 4 5; do echo "m${m}pc13 --pc 13 --mutant $m"; done; for m in 1 2 3 4 5; do echo "m${m}pc6 --pc 6 --mutant $m"; done; } | \
 xargs -P 14 -L 1 bash -c 'n=$0; nice -n 5 python3 '$SRC'/tools/qwen_static_kv/run_refresh_context_controller.py '$OUT'/$n "$@" > '$OUT'/$n.log 2>&1; echo "$n rc=$?" >> '$OUT'/done.txt'
echo ALLDONE >> $OUT/done.txt
