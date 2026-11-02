#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-pg-birth-0045
for c in repair_callback hold_control hold_callback repair_strict_v1; do
docker run --rm --network none --cpus 1 --memory 4g -v "$R":/work -e PG_READ_CASE="$c" openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /work/read_geometry.tcl' > "$R/read_geometry_${c}.log" 2>&1
done
