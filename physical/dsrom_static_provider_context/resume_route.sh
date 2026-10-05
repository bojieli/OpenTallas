#!/bin/bash
set -u
TASK_ROOT=$(realpath "$1")
ulimit -f unlimited
# Fresh clone of source-matched CTS artifacts; preserve all earlier failures.
# Routing layer settings are process-local: reapply at both routing stages.
# A routine hook correction; never edit old terminal work or accepted debts.
docker run --rm -v "$TASK_ROOT/src":/src:ro -v "$TASK_ROOT/work/orfs":/work \
 -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -lc \
 'trap '\''chmod -R a+rwX /work >/dev/null 2>&1 || true'\'' EXIT
 source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
 make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=4 PRE_CTS_TCL=/src/physical/dsrom_static_provider_context/clock.tcl POST_CTS_TCL=/src/physical/dsrom_static_provider_context/clock.tcl PRE_GLOBAL_ROUTE_TCL=/src/physical/dsrom_static_provider_context/routing_layers.tcl PRE_DETAIL_ROUTE_TCL=/src/physical/dsrom_static_provider_context/routing_layers.tcl finish metadata' \
 > "$TASK_ROOT/resume.log" 2>&1
TASK_STATUS=$?
printf '%s\n' "$TASK_STATUS" > "$TASK_ROOT/route.exit"
if [ "$TASK_STATUS" -eq 0 ]; then
 cd "$TASK_ROOT/src"
 python3 tools/w18/corner_sta.py --orfs-dir "$TASK_ROOT/work/orfs" --output "$TASK_ROOT/corner_sta.json" > "$TASK_ROOT/corner_sta.log" 2>&1
 TASK_STATUS=$?
 printf '%s\n' "$TASK_STATUS" > "$TASK_ROOT/sta.exit"
fi
printf '%s\n' "$TASK_STATUS" > "$TASK_ROOT/terminal.exit"
exit "$TASK_STATUS"
