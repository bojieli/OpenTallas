#!/bin/bash
set -euo pipefail
D=/srv/opentallas-scratch2/claude/codex-ring-nearmiss-1029
sudo docker run --rm --name codex-ring-final-clockdump-1029 --cpus=2 --memory=8g --memory-swap=8g -v "$D/kit_drt":/work:ro -v "$D":/out -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /out/dump_routed.tcl' > "$D/routed_dump.log" 2>&1
