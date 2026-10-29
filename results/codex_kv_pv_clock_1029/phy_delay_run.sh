#!/bin/bash
set -euo pipefail
K=$1
sudo docker run --rm --cpus 4 --memory 16g --memory-swap 16g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl >/dev/null; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=4 run RUN_SCRIPT=/work/phy_delay_run.tcl RUN_LOG_NAME_STEM=5_1_phy_delay HOLD_SLACK_MARGIN=5'
