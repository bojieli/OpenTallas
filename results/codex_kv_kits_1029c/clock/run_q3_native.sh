#!/bin/bash
set -euo pipefail
K=$1;GOAL=${2:-cts};MEM=${3:-48};N=${4:-8}
DK=docker;docker ps >/dev/null 2>&1 || DK='sudo docker'
$DK run --rm --cpus "$N" --memory "${MEM}g" --memory-swap "${MEM}g" -v "$K":/work -e HUID="$(id -u)" -e HGID="$(id -g)" -e GOAL="$GOAL" -e N="$N" -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
M="make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$N"
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/native_mm_patch.log 2>&1 || exit 9
python3 -I /work/kit_modes.py check /work --step grt --session "tc bc" --hold-repair || exit 9
R=$(ls -d /work/run/results/asap7/*/base | head -1)
$M -o "$R/3_place.odb" -o "$R/3_place.sdc" "$GOAL" > "/work/native_${GOAL}.log" 2>&1
rc=$?;tail -20 "/work/native_${GOAL}.log";chown -R "$HUID:$HGID" /work;exit $rc'
