#!/bin/bash
# QC-TOK link: tp8 / xdie / ovl4u on the bound_r8 constants (intel1)
RR=$(cd "$(dirname "$0")" && pwd); TB=$RR/tools_bound
export COLL_BENCH_ARGS="--relays 0 7 8 8 --lanes 2 2 10 2 2 10 --lx 12 4 12" MU_LS=389
export XQ_CUR="2,2,2,3,2,2/34,34,32,32,32,31,31" XQ_IMAGE=$RR/xdie/fx/img_bound/d2d_cal_image.svh XQ_TXDP_K="67,4,3,3"
export OVL_STAGES="$XQ_CUR"
mkdir -p $RR/logs
( TP8_PAR=4 bash $TB/stage_tp8_bound.sh $RR > $RR/logs/tp8.log 2>&1; echo "rc=$?" >> $RR/logs/tp8.log ) &
( JOBS=4 bash $TB/stage_xdie_bound.sh $RR > $RR/logs/xdie.log 2>&1; echo "rc=$?" >> $RR/logs/xdie.log ) &
( bash $TB/stage_ovl4u_bound.sh $RR --release-masters > $RR/logs/ovl4u.log 2>&1; echo "rc=$?" >> $RR/logs/ovl4u.log ) &
wait; echo ALL_DONE >> $RR/logs/done
