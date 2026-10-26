#!/bin/bash
# QC token side 10-25: one link stage (tp8 | xdie | ovl4u) on the meth bind constants (regen_constants on
# epyc1:/srv/opentallas-scratch2/claude/qc/bind_meth_cb16, KV peer kv41 bound_pv; kv44 gives the same xdie constants).
RR=$(cd "$(dirname "$0")" && pwd); TB=$RR/tools_bound; mkdir -p $RR/logs
export COLL_BENCH_ARGS="--relays 0 11 11 11 --lanes 2 2 21 2 2 20 --lx 23 4 22" MU_CAL=$RR/tp8/mu_cal_ls407.json
export XQ_CUR="2,2,2,3,2,2/34,34,32,32,32,31,31" XQ_IMAGE=$RR/xdie/fx/img_bound/d2d_cal_image.svh XQ_TXDP_K="67,4,3,3"
export OVL_STAGES="$XQ_CUR"
case "$1" in
  tp8)   TP8_PAR=${TP8_PAR:-6} bash $TB/stage_tp8_bound.sh $RR > $RR/logs/tp8.log 2>&1; rc=$?;;
  xdie)  JOBS=${JOBS:-4} bash $TB/stage_xdie_bound.sh $RR > $RR/logs/xdie.log 2>&1; rc=$?;;
  ovl4u) bash $TB/stage_ovl4u_bound.sh $RR --release-masters > $RR/logs/ovl4u.log 2>&1; rc=$?;;
  *) echo "usage: $0 tp8|xdie|ovl4u"; exit 2;;
esac
echo "rc=$rc" >> $RR/logs/$1.log; tail -5 $RR/logs/$1.log; exit $rc
