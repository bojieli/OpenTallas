#!/bin/bash
# run inside orfs container: /work = kit, /probe = this dir
set -e
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
cd /OpenROAD-flow-scripts/flow
M="make DESIGN_CONFIG=/work/config.mk WORK_HOME=/tmp/w FLOW_VARIANT=base"
export TC_LIB_FILES="$($M print-TC_LIB_FILES 2>/dev/null | sed -n 's/^TC_LIB_FILES: //p')"
export BC_LIB_FILES="$($M print-BC_LIB_FILES 2>/dev/null | sed -n 's/^BC_LIB_FILES: //p')"
export PLATFORM_DIR=/OpenROAD-flow-scripts/flow/platforms/asap7 PLATFORM=asap7
export RESULTS_DIR=/probe/res OT_HOLD_MM=1 OT_MM_SETUP_CORNER=tc OT_MM_FF_SDC=/probe/vclk_ff.sdc OT_RC_CAL=0
echo "libs TC: $TC_LIB_FILES"
openroad -no_init -threads 8 -exit /probe/single_probe.tcl 2>&1 | grep -E 'PROBE|Error'
openroad -no_init -threads 8 -exit /probe/mmspef_probe.tcl 2>&1 | grep -vE 'RSZ-0104|^\[INFO|WARNING STA-0450' | tail -30
