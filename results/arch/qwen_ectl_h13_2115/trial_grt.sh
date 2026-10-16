#!/bin/bash
set -euo pipefail
R=$1
C=$R/routes/gate/work/orfs
IMG=openroad/orfs:latest
docker run --rm -v "$R/src:/src:ro" -v "$C:/work" -w /OpenROAD-flow-scripts/flow "$IMG" bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts >/dev/null; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base GLOBAL_ROUTE_ARGS="-allow_congestion -verbose" GENERATE_ARTIFACTS_ON_FAILURE=1 grt' > "$R/h13_trial_grt.log" 2>&1
sed 's/4_1_cts.odb/5_1_grt.odb/' "$C/gate_layout_placed.tcl" > "$C/h13_trial_layout.tcl"
docker run --rm -e OT_LAYOUT_OUT=/work/h13_trial_layout.json -e OT_LAYOUT_CLOCKS=ck -e OT_LAYOUT_TOP=h13_trial -v "$R/src:/src:ro" -v "$C:/work" "$IMG" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/h13_trial_layout.tcl > "$R/h13_trial_layout.log" 2>&1
python3 "$R/src/tools/ref_tile/layout_png.py" "$C/h13_trial_layout.json" "$R/h13_trial_images" --congestion "$(find "$C/reports" -name congestion.rpt | head -1)"
echo H13_TRIAL_GRT_DONE
