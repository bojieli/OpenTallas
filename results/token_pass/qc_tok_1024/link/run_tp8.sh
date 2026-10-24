#!/bin/bash
RR=$(cd "$(dirname "$0")" && pwd)
export COLL_BENCH_ARGS="--relays 0 7 8 8 --lanes 2 2 10 2 2 10 --lx 12 4 12" MU_CAL=$RR/tp8/mu_cal_ls389.json
TP8_PAR=6 bash $RR/tools_bound/stage_tp8_bound.sh $RR > $RR/logs/tp8.log 2>&1; echo "rc=$?" >> $RR/logs/tp8.log
