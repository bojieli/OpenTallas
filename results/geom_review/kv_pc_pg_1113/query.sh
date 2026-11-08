#!/bin/bash
cd /
set -euo pipefail
D=/srv/opentallas-scratch2/claude/codex-kv-types-1113/pc_pg
docker run --rm --name codex-kv-pc-pg-query-1113 -v "$D:/out" openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /out/query.tcl > "$D/query.log" 2>&1
