#!/bin/bash
set -eu
K=/srv/opentallas-scratch2/claude/codex-hbm-rebal-0440/kit
docker run --rm --name codex-hnx-restore35-0440 --cpus 8 --memory 32g --memory-swap 32g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
set -e
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm_restore35.log 2>&1
mkdir -p /work/run/results/asap7/hbc_hnx_lane_x/base/restored35_input
cp /work/restored35_input/4_cts.sdc /work/run/results/asap7/hbc_hnx_lane_x/base/restored35_input/4_cts.sdc
cmp /work/restored35_input/4_cts.sdc /work/run/results/asap7/hbc_hnx_lane_x/base/5_1_grt.sdc
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 run RUN_SCRIPT=/work/restore_grt.tcl > /work/restore35.log 2>&1
'
