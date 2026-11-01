#!/bin/bash
set -euo pipefail
K=$(realpath "$1")
docker run --rm --name codex-caprt-final-$(basename "$K")-$$ --cpus=8 --memory=8g --memory-swap=8g -v "$K":/work -e HUID=$(id -u) -e HGID=$(id -g) -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl || exit 9
rc=0
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 SETUP_SLACK_MARGIN=20 HOLD_SLACK_MARGIN=10 RUN_SCRIPT=/work/core_final_repair_resume.tcl RUN_LOG_NAME_STEM=core_final_repair1131 run || rc=$?
chown -R "$HUID:$HGID" /work
exit "$rc"
' > "$K/run_final_repair1131.log" 2>&1
