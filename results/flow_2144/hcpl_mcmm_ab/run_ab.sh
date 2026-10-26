#!/bin/bash
set -uo pipefail
K=$(cd "$1" && pwd)
MODE=$(cat "$K/ab_mode.txt")
NAME=codex-hcpl-grt-${MODE}-$$
docker run --rm --name "$NAME" --cpus=8 --memory=24g --memory-swap=24g -v "$K":/work -e MODE="$MODE" -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
C=bc; if [ "$MODE" = mm ]; then C="tc bc"; fi
sha256sum /work/run/results/asap7/*/base/4_cts.odb /work/config.mk > /work/ab_inputs.sha256
OT_VCLK_CORNER=ff make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 grt CORNER=BC "CORNERS=$C" HOLD_SLACK_MARGIN=5 > /work/ab_grt.log 2>&1
RC=$?; echo "$RC" > /work/ab_grt.rc
if [ "$RC" = 0 ]; then
  python3 -I /work/legacy_gate.py /work grt > /work/ab_gate.log 2>&1
  echo "$?" > /work/ab_gate.rc
fi
chown -R 1000:1000 /work
exit "$RC"
'
