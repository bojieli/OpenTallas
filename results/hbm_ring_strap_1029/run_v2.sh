#!/bin/bash
# HBM-CORES-KITS-10 ring V2 (structural): strap_qid ECO'd retained CTS (clock cells FIRM, tree unchanged) -> GRT with
# SLEW_MARGIN 50 / CAP_MARGIN 20 / FF hold margin 10 -> DRT -> finish -> abstract -> kit post sign-off.
set -uo pipefail
W=/srv/opentallas-scratch2/claude/kits10-1029/ring; K=$W/v2
docker run --rm --name k10-ring-v2 --cpus=16 --memory=40g --memory-swap=40g -v "$K":/work -e HUID=$(id -u) -e HGID=$(id -g) -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm_v2.log 2>&1 || exit 9
python3 -I /work/kit_modes.py check /work --step grt --session "tc bc" --hold-repair > /work/kit_modes_v2.log 2>&1 || exit 9
M="make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=16 SLEW_MARGIN=50 CAP_MARGIN=20 HOLD_SLACK_MARGIN=10 OT_HOLD_FF_MARGIN=10"
$M do-5_1_grt > /work/v2_grt.log 2>&1; rc=$?
if [ $rc = 0 ]; then $M do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc > /work/v2_drt.log 2>&1; rc=$?; fi
if [ $rc = 0 ]; then $M do-finish > /work/v2_finish.log 2>&1; rc=$?; fi
if [ $rc = 0 ]; then $M do-generate_abstract > /work/v2_abstract.log 2>&1; rc=$?; fi
chown -R "$HUID:$HGID" /work
exit $rc
' > $W/v2_client.log 2>&1
rc=$?; echo "V2_FLOW_RC $rc $(date)" >> $W/v2_client.log
[ $rc = 0 ] && bash $K/run_kit_hbm.sh $K post 32 8 > $W/v2_post.log 2>&1
echo "V2_DONE $rc $(date)" >> $W/v2_client.log
