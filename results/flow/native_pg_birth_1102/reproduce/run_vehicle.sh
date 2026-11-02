#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-pg-birth-0045
for c in control callback; do
 docker run --rm --network none --cpus 1 --memory 4g -v "$R":/work -e PG_CASE="$c" openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -no_init -exit /work/repair_vehicle.tcl' > "$R/repair_$c.log" 2>&1
done
