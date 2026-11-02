#!/bin/bash
set -euo pipefail
mkdir -p run/results/asap7/kq_qfd_qc_su_lane_w_l1_w0e61bf/base run/reports/asap7/kq_qfd_qc_su_lane_w_l1_w0e61bf/base
exec docker run --rm --cpus 4 --memory 32g --memory-swap 32g -v "$PWD":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/mm_patch.log
python3 /work/route_input_adapter.py /OpenROAD-flow-scripts/flow/scripts > /work/input_adapter.json
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=4 do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=4 do-finish
' > route.log 2>&1
