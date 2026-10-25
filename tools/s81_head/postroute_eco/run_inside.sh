#!/bin/bash
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
cd /OpenROAD-flow-scripts/flow
M=(make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=16)
export OT_MAX_FANOUT=24 OT_SLEW_MARGIN=20 OT_SETUP_MARGIN=10 OT_HOLD_MARGIN=5 OT_HOLD_ALLOW_SETUP=1 OT_HOLD_MAXBUF=40 OT_DRV_LAST=1 OT_RETIME_LAST=1
"${M[@]}" do-route CORNER=TC 'CORNERS=tc bc' SKIP_INCREMENTAL_REPAIR=1
"${M[@]}" do-finish
"${M[@]}" do-generate_abstract
TOP=$(sed -n 's/^export DESIGN_NAME = //p' /work/config.mk)
F=$(find /work/run/results/asap7 -name 6_final.odb | head -1)
ODB="$F" PINS=/work/pins.json OUT=/work/pin_audit.json openroad -python -exit /work/pin_audit.py
for c in TT FF; do OT_CORNER=$c DESIGN_NAME="$TOP" ODB="$F" SPEF="${F%.odb}.spef" openroad -exit /work/corners.tcl > /work/sta_${c}.log 2>&1; done
