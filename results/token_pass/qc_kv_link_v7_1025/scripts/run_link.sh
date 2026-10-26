#!/bin/bash
# TOK-QK-XD2 10-25: one link stage (tp8 | xdie | ovl4u) on the QC v7 final bind constants (regen_constants --peer b19 on the
# rebind of physical/die_plan/qwen_compute/die_plan.json @ the assembly commit, KV peer = strict bind b19).
RR=$(cd "$(dirname "$0")" && pwd); TB=$RR/tools_bound; mkdir -p $RR/logs
export COLL_BENCH_ARGS="${COLL_BENCH_ARGS:---relays 0 11 11 11 --lanes 2 2 21 2 2 21 --lx 23 4 23}" MU_CAL=$RR/tp8/mu_cal_ls407.json
export XQ_CUR="2,2,2,3,2,2/56,56,54,54,54,55,55" XQ_IMAGE=$RR/xdie/fx/img_bound/d2d_cal_image.svh XQ_TXDP_K="113,4,3,3"
export OVL_STAGES="$XQ_CUR"
case "$1" in
  tp8)   TP8_PAR=${TP8_PAR:-6} bash $TB/stage_tp8_bound.sh $RR > $RR/logs/tp8.log 2>&1; rc=$?;;
  xdie)  JOBS=${JOBS:-4} bash $TB/stage_xdie_bound.sh $RR > $RR/logs/xdie.log 2>&1; rc=$?;;
  ovl4u) bash $TB/stage_ovl4u_bound.sh $RR --release-masters > $RR/logs/ovl4u.log 2>&1; rc=$?;;
  *) echo "usage: $0 tp8|xdie|ovl4u"; exit 2;;
esac
echo "rc=$rc" >> $RR/logs/$1.log; tail -5 $RR/logs/$1.log; exit $rc
