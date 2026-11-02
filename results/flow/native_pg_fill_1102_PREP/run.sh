#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-pg-birth-fill-0312
for fill_case in missing_L control callback; do
 docker run --rm --network none --memory=4g --memory-swap=4g --cpus=1 -v "$R":/work -e PG_FILL_CASE="$fill_case" openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 1 -exit /work/vehicle.tcl' > "$R/fill_${fill_case}.log" 2>&1
done
cmp -s "$R/fill_control_geometry.txt" "$R/fill_callback_geometry.txt"
docker run --rm --network none --memory=4g --memory-swap=4g --cpus=1 -v "$R":/work -e OT_PG_AUDIT_ODB=/work/fill_callback.odb -e OT_PG_AUDIT_REPORT=/work/saved_fill_callback_pg.json openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 1 -exit /work/audit_native_pg.tcl' > "$R/saved_fill_callback_pg.log" 2>&1
