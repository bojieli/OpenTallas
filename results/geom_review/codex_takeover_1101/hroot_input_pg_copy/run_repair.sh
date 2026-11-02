#!/bin/bash
set -uo pipefail
K=$(pwd)
C=codex-hroot-pg-copy-0205-$$
printf '%s\n' "$C" > repair_container.txt
docker run --rm --name "$C" --memory=8g --memory-swap=8g --cpus=1 -v "$K":/work -v "$K/input.odb":/input/3_place.odb:ro -w /work -e HUID=$(id -u) -e HGID=$(id -g) openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
openroad -exit /work/repair_pg.tcl
rc=$?
if [ "$rc" = 0 ]; then openroad -python -exit /work/guard_pg.py; rc=$?; fi
if [ "$rc" = 0 ]; then OT_PG_AUDIT_ODB=/work/hroot_pg_bound.odb OT_PG_AUDIT_REPORT=/work/saved_pg.json openroad -exit /work/audit_native_pg.tcl; rc=$?; fi
chown -R "$HUID:$HGID" /work/*json /work/hroot_pg_bound.odb 2>/dev/null || true
exit "$rc"
' > repair.log 2>&1
rc=$?
printf '%s\n' "$rc" > repair_exit.txt
exit "$rc"
