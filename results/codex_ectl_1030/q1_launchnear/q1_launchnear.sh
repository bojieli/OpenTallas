#!/bin/bash
set -uo pipefail
D=/srv/opentallas-scratch2/claude/codex-ectl-1030/q1_launchnear
rc=0
docker run --rm --name codex-q1-launchnear-1030 --cpus=8 --memory=24g --memory-swap=24g -v "$D":/work -v "$D":/out -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; export OT_LIBS="$(make -s DESIGN_CONFIG=/work/config.mk WORK_HOME=/tmp/q1launch print-TC_LIB_FILES 2>/dev/null | sed "s/^[A-Z_]*: //")"; openroad -exit /work/q1_launchnear.tcl' > "$D/placement3.log" 2>&1 || rc=$?
docker run --rm -v "$D":/work openroad/orfs:asap7lock chown -R 1000:1000 /work
exit "$rc"
