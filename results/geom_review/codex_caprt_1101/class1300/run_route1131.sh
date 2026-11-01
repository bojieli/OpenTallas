#!/bin/bash
set -euo pipefail
K=$(realpath "$1"); TOOLS=$(realpath "$2"); MEM=${3:-24}; CPUS=${4:-8}; MARGIN=${5:-20}
NAME=codex-caprt-route1131-$(basename "$K")-$$
docker run --rm --name "$NAME" --cpus="$CPUS" --memory="${MEM}g" --memory-swap="${MEM}g" -v "$K":/work -v "$TOOLS":/m:ro -e HUID=$(id -u) -e HGID=$(id -g) -e OT_ROUTE_THREADS="$CPUS" -e OT_ROUTE_SETUP_MARGIN="$MARGIN" -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
# Each stage uses a fresh container: reinstall the same released two-mode hook.
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm_route1131.log 2>&1 || { cat /work/orfs_hold_mm_route1131.log; exit 9; }
rc=0
python3 -I /m/legacy_gate.py /work grt > /work/grt_policy_route1131.log 2>&1 || rc=$?
cat /work/grt_policy_route1131.log
if [ "$rc" = 0 ]; then
 M="make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$OT_ROUTE_THREADS SETUP_SLACK_MARGIN=$OT_ROUTE_SETUP_MARGIN HOLD_SLACK_MARGIN=10"
 $M do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc || rc=$?
 if [ "$rc" = 0 ]; then $M do-finish do-generate_abstract || rc=$?; fi
 if [ "$rc" = 0 ]; then
  F=$(ls /work/run/results/asap7/*/base/6_final.odb | tail -1)
  ODB="$F" PINS=/work/pins.json OUT=/work/pin_audit1131.json openroad -python -exit /work/pin_audit.py > /work/pin_audit1131.log 2>&1 || rc=$?
 fi
fi
chown -R "$HUID:$HGID" /work
exit "$rc"
' > "$K/run_route1131.log" 2>&1
