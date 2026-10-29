#!/bin/bash
set -euo pipefail
K=/srv/opentallas-scratch2/claude/codex-qc-a0-2340/parent_reset
docker run --rm --name codex-qca0-parent-reset-place --cpus=8 --memory=32g --memory-swap=32g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 -I /work/rtl_lint.py /work > /work/rtl_lint_reset.log 2>&1 || exit $?
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 place
rc=$?;chown -R 1000:1000 /work;exit $rc' > "$K/reset_place.log" 2>&1
