#!/bin/bash
set -euo pipefail
K=$(realpath "$1"); TOOLS=$(realpath "$2"); MEM=${3:-8}; CPUS=${4:-8}
NAME=codex-caprt-route-$(basename "$K")-$$
docker run --rm --name "$NAME" --cpus="$CPUS" --memory="${MEM}g" --memory-swap="${MEM}g" -v "$K":/work -v "$TOOLS":/m:ro -e HUID=$(id -u) -e HGID=$(id -g) -e OT_ROUTE_THREADS="$CPUS" -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
rc=0
python3 -I /m/legacy_gate.py /work grt > /work/grt_policy_codex.log 2>&1 || rc=$?
cat /work/grt_policy_codex.log
if [ "$rc" = 0 ]; then
  M="make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$OT_ROUTE_THREADS SETUP_SLACK_MARGIN=100 HOLD_SLACK_MARGIN=10"
  $M do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc || rc=$?
  if [ "$rc" = 0 ]; then $M do-finish do-generate_abstract || rc=$?; fi
fi
chown -R "$HUID:$HGID" /work
exit "$rc"
' > "$K/run_route_codex.log" 2>&1
