#!/bin/bash
set -euo pipefail
D=/srv/opentallas-scratch2/claude/codex-pv-clkfreeze-0336
K=/srv/opentallas-scratch2/claude/codex-ectl-1030/pv_pad_proto5
docker run --rm --name codex-pv-clkfreeze0336-final --cpus=2 --memory=8g --memory-swap=8g -v "$K":/work:ro -v "$D":/out -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; export OT_LIBS="$(make -s DESIGN_CONFIG=/work/config.mk WORK_HOME=/tmp/pcdrive print-TC_LIB_FILES 2>/dev/null | sed "s/^[A-Z_]*: //")"; openroad -exit /out/probe_final.tcl' > "$D/probe_final.log" 2>&1
