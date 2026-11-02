#!/bin/bash
set -uo pipefail
R=/srv/opentallas-scratch2/claude/codex-bfqg-guides-access-pg-0035
K=/srv/opentallas-scratch2/claude/codex-bfqg-residual-guides-prep-2350/kit
base=(sudo docker run --rm --cpus 2 --memory 2g --memory-swap 2g -v "$K":/work:ro -v "$R":/out -w /out -e HUID="$(id -u)" -e HGID="$(id -g)")
"${base[@]}" --name "codex-bfqg-guide-pg-$$" -e OT_PG_AUDIT_ODB=/work/run/results/asap7/hbc_ot_hgi_sm_xload_cl2_bfqg/base/3_place.odb -e OT_PG_AUDIT_REPORT=/out/pg.json openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /out/audit_native_pg.tcl > /out/pg.log 2>&1; rc=$?; chown $HUID:$HGID /out/pg*; exit $rc'
pgrc=$?
"${base[@]}" --name "codex-bfqg-guide-access-$$" -e ODB=/work/run/results/asap7/hbc_ot_hgi_sm_xload_cl2_bfqg/base/3_place.odb -e OUT=/out/access.json openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -python -exit /out/access.py > /out/access.log 2>&1; rc=$?; chown $HUID:$HGID /out/access*; exit $rc'
arc=$?
[ "$arc" = 0 ] || exit "$arc"
exit "$pgrc"
