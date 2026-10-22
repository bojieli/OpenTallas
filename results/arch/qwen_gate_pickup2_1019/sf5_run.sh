#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch/claude/ref_gate/qfd_d2d_static_sf5-20261019-115442
for C in tt ff; do
 docker run --rm -e OT_GATE_SIGNOFF_SDC=/src/physical/ref_tile/qfd_d2d_static_sf5/signoff.sdc -v "$R/src:/src:ro" -v "$R/routes/gate/work/orfs:/work" -v "$R/pickup_$C.tcl:/probe.tcl:ro" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /probe.tcl > "$R/pickup_native_$C.log" 2>&1
 done
 echo PICKUP_NATIVE_TT_FF_DONE
