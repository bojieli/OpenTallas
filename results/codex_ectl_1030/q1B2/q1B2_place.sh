#!/bin/bash
set -uo pipefail
D=/srv/opentallas-scratch2/claude/codex-ectl-1030/q1B2_place
rc=0
docker run --rm --name codex-q1B2-place-1030 --cpus=8 --memory=24g --memory-swap=24g -v "$D":/work -v "$D":/out -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; export OT_LIBS="$(make -s DESIGN_CONFIG=/work/config.mk WORK_HOME=/tmp/pcdrive print-TC_LIB_FILES 2>/dev/null | sed "s/^[A-Z_]*: //")"; openroad -exit /work/q1B2_place.tcl' > "$D/placement.log" 2>&1 || rc=$?
docker run --rm -v "$D":/work openroad/orfs:asap7lock chown -R 1000:1000 /work
exit "$rc"
