#!/bin/bash
# HBM-CORES-KITS-13 ring V1b: driver upsize ECO (v1b_eco.tcl) on V1 5_1_grt -> DRT -> finish -> abstract -> kit post sign-off.
set -uo pipefail
W=/srv/opentallas-scratch2/claude/kits10-1029/ring; K=$W/v1b
R=$K/run/results/asap7/hbc_ot_hfd_coll_q2_hard_v8g__ring_ag/base
docker run --rm --name k13-ring-v1b --cpus=16 --memory=40g --memory-swap=40g -v "$K":/work -v "$W":/out -e HUID=$(id -u) -e HGID=$(id -g) -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm_v1b.log 2>&1 || exit 9
M="make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=16"
$M RUN_SCRIPT=/out/v1b_eco.tcl RUN_LOG_NAME_STEM=v1b_eco run > /work/v1b_eco.log 2>&1 || exit 7
$M do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc > /work/v1b_drt.log 2>&1; rc=$?
if [ $rc = 0 ]; then $M do-finish > /work/v1b_finish.log 2>&1; rc=$?; fi
if [ $rc = 0 ]; then $M do-generate_abstract > /work/v1b_abstract.log 2>&1; rc=$?; fi
chown -R "$HUID:$HGID" /work
exit $rc
' > $W/v1b_client.log 2>&1
rc=$?; echo "V1B_FLOW_RC $rc $(date)" >> $W/v1b_client.log
[ $rc = 0 ] && bash $K/run_kit_hbm.sh $K post 32 8 > $W/v1b_post.log 2>&1
echo "V1B_DONE $rc $(date)" >> $W/v1b_client.log
