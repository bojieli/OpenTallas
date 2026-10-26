#!/bin/bash
# QC-SU-BTAB 2026-10-26: btab_r6 candidate -> sign-off chain on the UNCHANGED R6 clock (12.8: no clock edits after measurement).
# 1 stageA_post.sh: pin-reg I measure TT/FF (main RCX basis) -> IO vclk bound (constraint only) -> hold_s6.sh FF-only DATA-PATH
#   hold repair (repair_timing -hold, margin 15; no clock cells touched) + pre-route insertion gate.
# 2 PG binding (claude/flow-pg-final-1026@eda7910d2 pg_connect.tcl, not merged on main): ot_pg_connect_all + ot_pg_require_bound on 5_1_grt.odb.
# 3 run_kit.sh: DRT -> fill -> final -> abstract -> so_exact/signoff.py (flow-pg-final copy: pg is a BLOCKING check) tt,ff --ff-vclk auto.
set -uo pipefail
K=/srv/opentallas-scratch2/claude/qc-su-lat-r6/btab_r6; IMAGE=openroad/orfs:asap7lock
HB=$K/run/results/asap7/kq_qfd_dv_s8x_btab_aspect1713a1/base; B=/work/run/results/asap7/kq_qfd_dv_s8x_btab_aspect1713a1/base
log(){ echo "R6CHAIN $* $(date -Is)" | tee -a $K/r6_chain.status; }
log start
[ -f $HB/5_1_grt_cal.odb ] || { cp $HB/5_1_grt.odb $HB/5_1_grt_cal.odb; cp $HB/route.guide $HB/route_cal.guide; }
cp $HB/5_1_grt_cal.odb $HB/5_1_grt_prehold.odb
mv $K/s6_grt_gate.txt $K/s6_grt_gate.stale_s8.txt 2>/dev/null
$K/stageA_post.sh $K > $K/r6_stageA_post.log 2>&1; rc=$?
log stageA_post rc $rc; [ $rc = 0 ] || exit $rc
docker run --rm --name qcsu-btab-r6-pg-$$ --cpus=2 --memory=8g --memory-swap=8g -v "$K":/work -w /work -e OT_PG_ODB=$B/5_1_grt.odb -e OT_PG_WRITE=1 $IMAGE bash -lc \
 "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /work/r6_pg.tcl" > $K/r6_pg_pre_drt.log 2>&1; rc=$?
docker run --rm -v "$K":/work $IMAGE chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
log pg_pre_drt rc $rc $(grep -h 'OT_PG' $K/r6_pg_pre_drt.log | tr '\n' ' '); [ $rc = 0 ] || exit 7
$K/run_kit.sh $K route 24 8 > $K/r6_run_kit.log 2>&1; rc=$?
log run_kit rc $rc; exit $rc
