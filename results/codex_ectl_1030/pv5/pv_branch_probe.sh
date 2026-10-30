#!/bin/bash
D=/srv/opentallas-scratch2/claude/codex-ectl-1030/pv_pad_proto5
docker run --rm --name codex-pvbranch-1030 --cpus=2 --memory=4g --memory-swap=4g -v "$D":/work:ro -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /work/pv_branch_probe.tcl' > "$D/branch_probe.log" 2>&1
