#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-pg-birth-0045
for case in hold_callback repair_strict_v1; do
 docker run --rm --network none --cpus 1 --memory 4g -v "$R":/work -e OT_PG_AUDIT_ODB="/work/$case.odb" -e OT_PG_AUDIT_REPORT="/work/${case}_saved_audit.json" openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /work/audit_native_pg.tcl' > "$R/${case}_saved_audit.log" 2>&1
done
