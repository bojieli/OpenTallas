#!/bin/bash
set -euo pipefail
K=$(cd "$(dirname "$0")/kit" && pwd)
R=$K/run/results/asap7/hbc_hnx_lane_x/base
mkdir -p "$K/pre_input_pad_cts"
cp "$R/4_cts.odb" "$K/pre_input_pad_cts/4_cts.odb"
cp "$R/4_cts.sdc" "$K/pre_input_pad_cts/4_cts.sdc"
cp --remove-destination "$K/cts_input_pad/4_cts.odb" "$R/4_cts.odb"
cp --remove-destination "$K/cts_input_pad/4_cts.sdc" "$R/4_cts.sdc"
docker run --rm --name codex-hnx-pad-grt-0310 --cpus 16 --memory 32g --memory-swap 32g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
set -e
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm_grt_pad.log 2>&1
python3 -I /work/kit_modes.py check /work --step grt --session "tc bc" --hold-repair > /work/kit_modes_grt_pad.log 2>&1
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=16 grt HOLD_SLACK_MARGIN=0 > /work/run_grt_pad.log 2>&1
'
