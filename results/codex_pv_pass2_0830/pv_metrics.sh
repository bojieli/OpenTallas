#!/bin/bash
set -e
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
for pv_corner in TT FF; do
 export PV_CORNER=$pv_corner
 export OT_VCLK_CORNER=${pv_corner,,}
 export PV_LIBS=$(find /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -maxdepth 1 -name "asap7sc7p5t_*RVT_${pv_corner}_*.lib*" | sort | tr '\n' ' ')
 openroad -exit /work/pv_clock_metrics.tcl > /work/pv_cts_${pv_corner}_metrics.log 2>&1
done
