#!/bin/bash
set -euo pipefail
K=$(pwd)
for c in TT FF; do
 docker run --rm --cpus=4 --memory=8g --memory-swap=8g -v "$K":/work -w /work -e OT_CORNER=$c -e OT_POSTCTS_GRT=1 -e ODB=/work/run/results/asap7/kq_qfd_dv_s8x_vmr_rw60/base/5_1_grt.odb -e LAYER_PARASITICS_FILE=/work/cf/rc_cal.tcl -e OT_RC_CAL=0.8,0.9 -e OT_MSCTS_SPEC=/work/mscts_spec.tcl -e OT_MSCTS_CORR=/work/mscts_corr.tcl openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /work/readiness_native_v2.tcl' > "$K/current_native_v2_${c}.log" 2>&1
done
