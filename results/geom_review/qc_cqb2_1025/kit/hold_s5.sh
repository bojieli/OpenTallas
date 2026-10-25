#!/bin/bash
# QC-CQB2 vmr_s5: FF-only GRT hold step (hold_grt_s5.tcl) in docker; log run_hold.log
set -uo pipefail
K=$(cd "$(dirname "$0")" && pwd); IMAGE=openroad/orfs:asap7lock
echo "image $IMAGE host $(hostname) hold start $(date -Is)" >> "$K/image.txt"
docker run --rm --name qccqb2-s5-hold-$$ --cpus=8 --memory=16g --memory-swap=16g -v "$K":/work -w /work \
  -e RESULTS_DIR=/work/run/results/asap7/kq_qfd_dv_s8x_vmr_rw60/base -e OT_RC_CAL=0.8,0.9 -e OT_S5_HOLD_MARGIN=${OT_S5_HOLD_MARGIN:-15} $IMAGE \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 8 -exit /work/hold_grt_s5.tcl" > "$K/run_hold.log" 2>&1
rc=$?
docker run --rm -v "$K":/work $IMAGE chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
echo "end hold $(date -Is) rc $rc" >> "$K/image.txt"; tail -4 "$K/run_hold.log"; exit $rc
