#!/bin/bash
set -euo pipefail
K=$(realpath "$1"); MARGIN=${2:-100}; MEM=${3:-8}; CPUS=${4:-8}
NAME=codex-caprt-grt-$(basename "$K")-$$
docker run --rm --name "$NAME" --cpus="$CPUS" --memory="${MEM}g" --memory-swap="${MEM}g" -v "$K":/work -e OT_GRT_MARGIN="$MARGIN" -e HUID=$(id -u) -e HGID=$(id -g) -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm_grt.log 2>&1
rc=0
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 SETUP_SLACK_MARGIN=$OT_GRT_MARGIN HOLD_SLACK_MARGIN=10 do-grt || rc=$?
chown -R "$HUID:$HGID" /work
exit "$rc"
' > "$K/run_grt_codex.log" 2>&1
