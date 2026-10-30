#!/bin/bash
set -euo pipefail
K=$1
mkdir -p "$K/diag_out"
cat > "$K/dpl_trial.tcl" <<'TCL'
set_thread_count 4
set ::env(RESULTS_DIR) /work/diag_out
set ::env(REPORTS_DIR) /work/diag_out
set ::env(OT_RELAY_MID_RE) {^(.*[.]u_y_[A-Za-z0-9_]+)[.]}
read_db /work/run/results/asap7/dp_hd_tile/base/3_place.odb
source /work/face_flops.tcl
source /work/tile_hop.tcl
detailed_placement
check_placement -verbose
write_db /work/diag_out/3_place.odb
TCL
docker run --rm --name codex-head-tile3-dpl --cpus=4 --memory=16g --memory-swap=16g -v "$K":/work -w /work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /work/dpl_trial.tcl'
