#!/bin/bash
# HBM-CORES-KITS-13 (m10b = m10 + mp_isl M5 track snap, isl_snap.tcl): HNX restored35 margin10 (TT +18.85 / FF +8.56 / slew 0 / cap 0, clock identical) -> DRT -> finish -> abstract -> signoff.
set -u
K=/srv/opentallas-scratch2/claude/codex-hbm-rebal-0440/kit
B=$K/run/results/asap7/hbc_hnx_lane_x/base
[ -f $B/5_1_grt_pre_m10.odb ] || cp $B/5_1_grt.odb $B/5_1_grt_pre_m10.odb
[ -f $B/5_1_grt_pre_m10.sdc ] || cp $B/5_1_grt.sdc $B/5_1_grt_pre_m10.sdc
docker run --rm --memory 8g -v "$K":/work -v /srv/opentallas-scratch2/claude/codex-hbm-rebal-0440:/d -e ODB_IN=/work/margin10/5_1_grt.odb -e ODB_OUT=/work/run/results/asap7/hbc_hnx_lane_x/base/5_1_grt.odb openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /d/isl_snap.tcl" > /srv/opentallas-scratch2/claude/codex-hbm-rebal-0440/isl_snap.log 2>&1 || exit 5; grep -q ISL_SNAP_COUNT /srv/opentallas-scratch2/claude/codex-hbm-rebal-0440/isl_snap.log || exit 5; cp $K/margin10/5_1_grt.sdc $B/5_1_grt.sdc
rm -f $B/5_2_route.odb $B/5_3_fillcell.odb $B/5_route.odb $B/5_route.sdc $B/6_1_fill.odb $B/6_final.*
docker run --rm --name k13-hnx-drt --cpus 16 --memory 40g --memory-swap 40g -v "$K":/work -e HUID=$(id -u) -e HGID=$(id -g) -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm_drtb.log 2>&1 || exit 9
M="make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=16"
$M do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc > /work/m10b_drt.log 2>&1; rc=$?
if [ $rc = 0 ]; then $M do-finish > /work/m10b_finish.log 2>&1; rc=$?; fi
if [ $rc = 0 ]; then $M do-generate_abstract > /work/m10b_abstract.log 2>&1; rc=$?; fi
chown -R "$HUID:$HGID" /work
exit $rc
'
rc=$?; echo "M10B_FLOW_RC $rc $(date)"
if [ $rc = 0 ]; then python3 $K/signoff.py run --run-dir $K/run --kit $K --corners tt,ff --out $K/signoff_m10b --docker docker; echo "M10B_SIGNOFF_RC $? $(date)"; fi
echo "M10B_DONE $(date)"
