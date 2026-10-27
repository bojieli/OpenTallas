#!/bin/bash
# Placement only, from the preserved and patched R6 synthesis checkpoint.
set -euo pipefail
K=$(realpath "$1")
MEM=${2:-32}
CPUS=${3:-16}
docker run --rm --name codex-head-replace-$$ --cpus="$CPUS" --memory="${MEM}g" --memory-swap="${MEM}g" \
  -v "$K":/work -e HUID="$(id -u)" -e HGID="$(id -g)" -e CPUS="$CPUS" \
  -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
    set -euo pipefail
    source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
    python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm.log
    grep -q "status.: .patched." /work/orfs_hold_mm.log
    R=/work/run/results/asap7/hd_elemB_rb/base
    test -f "$R/2_floorplan.odb"
    # do-place uses the pinned floorplan directly; aggregate place would remake
    # synthesis because the new config/pins have newer modification times.
    # The original 2_floorplan is unchanged; do-3_2_place_iop applies the new pins.
    make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES="$CPUS" do-place
    ODB="$R/3_place.odb" OUT=/work/elemB_replaced.geo openroad -exit /work/dump_geo_head.tcl
    chown -R "$HUID:$HGID" /work
  ' > "$K/replace.log" 2>&1
