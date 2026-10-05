#!/bin/bash
set -u
D=/srv/opentallas-scratch/codex/noether-spine-current-E1-20261005
W=$D/source-39c300098
J=$D/jobs/E1_current_cts1
mkdir -p "$J"
export WT=$W RUN=E1_current_cts1 K=1 STOP=cts
export OT_SPINE_JOB_ROOT=$D/jobs OT_ORFS_NUM_CORES=16 OT_SPINE_REPIN_E1=0
/srv/opentallas-scratch/admit.sh 32 -- "$W/results/rtl/rom_stage_spine_cdc_20261004/launch.sh" > "$D/budget_prefix.log" 2>&1
rc=$?
echo "$rc" > "$D/budget_prefix.rc"
R=$J/work/orfs
B=$R/results/asap7/opentallas_ot_v41_rom_stage_q_pg_cdc_w10_asap7_spine_cdc_E1_current_cts1_20261004/base
if [ -f "$B/4_cts.odb" ] && [ -f "$B/4_cts.sdc" ]; then
 /srv/opentallas-scratch/admit.sh 4 -- docker run --rm -v "$D:/query" -v "$W:/src:ro" -v "$R:/work:ro" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /query/query_current.tcl > "$D/query_current.log" 2>&1
 echo "$?" > "$D/query_current.rc"
fi
# Stops here. No global route, no automatic retry, no margin transfer or energy credit.
