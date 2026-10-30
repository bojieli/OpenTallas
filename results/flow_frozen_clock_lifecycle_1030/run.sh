#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-hbm-cores-1030
O=/srv/opentallas-scratch2/claude/codex-ring-lifecycle-0336
docker run --rm --name codex-ring-lifecycle0336 --cpus=2 --memory=20g --memory-swap=20g -v "$R/ring_slew50":/work:ro -v "$R/ring_five_dpl":/baseline:ro -v "$R/ring_rc_control":/qualified:ro -v "$O":/out -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; M="make -s DESIGN_CONFIG=/work/config.mk WORK_HOME=/tmp/rc_lifecycle"; export OT_TC_LIBS="$($M print-TC_LIB_FILES 2>/dev/null | sed "s/^[A-Z_]*: //")" OT_BC_LIBS="$($M print-BC_LIB_FILES 2>/dev/null | sed "s/^[A-Z_]*: //")"; openroad -exit /out/control.tcl' > "$O/control.log" 2>&1
